import asyncio
import aiohttp
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import sys
import random
import re
import argparse
import os
import time

save_to_directory = os.path.join(os.path.expanduser("~"), "Downloads")
dict_streams = {
    "groove-1": {"url": "https://ice2.somafm.com/groovesalad-128-aac", "ext": "aac"},
    "groove-2": {"url": "https://ice2.somafm.com/groovesalad-128-aac", "ext": None},
    # example of no extension being defined, default to guessing from station URL
}

expected_content_type = "audio/*"
name_seperator = "_"
web_headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
}
chunk_size = 1024

parser = argparse.ArgumentParser()
parser.add_argument("-u", "--url", type=str, help="url of stream")
parser.add_argument("-n", "--name", type=str, help="shortname of stream e.g. raw_fm")
parser.add_argument("-d", "--directory", type=str, help="directory to save files to")
args = parser.parse_args()
args_provided = False


def update_time():
    global current_time
    current_time = datetime.now().replace(microsecond=0).isoformat().replace(":", "-")


async def record_station(station_name, station_url, ext=None):
    global current_time
    last_used_fn = None
    first_time_attempts = 0
    retry_attempts = 0
    run_before = False
    error_time = False
    utc_offset = time.strftime("%z")
    tz_name = datetime.now().astimezone().tzname()
    cleanurl = station_url.rstrip("/")
    if ext:
        file_extension = "." + ext.lstrip(".")
    else:
        file_extension = "." + cleanurl.split("/")[-1].split(".")[-1]

    standard_file_name = utc_offset + name_seperator + station_name + file_extension
    session = aiohttp.ClientSession()
    while True:
        try:
            if error_time:
                print(
                    f"Could not connect to {station_name} stream, retrying after {sleep_time} seconds. Retry attempt #{retry_attempts}."
                )
                await asyncio.sleep(sleep_time)
            if not run_before:
                first_time_attempts += 1
                print(
                    f"Attempting initial connection to {station_name}... attempt number #{first_time_attempts}."
                )
                if first_time_attempts < 2:
                    await asyncio.sleep(5)
                else:
                    await asyncio.sleep(random.randrange(5, 60))
            async with session.get(
                station_url,
                timeout=aiohttp.ClientTimeout(total=None, sock_connect=5, sock_read=20),
                headers=web_headers,
                # sock_read 5 is usually ok. Can cause issues if stream inconsistently sends data. 20 is used for safety.
            ) as resp:
                retry_attempts = 0
                if not re.match(expected_content_type, resp.headers["content-type"]):
                    sys.exit("Server's content-type is not audio. Check the link.")
                if not run_before and resp.status == 404:
                    sys.exit("URL is 404. Check the link.")
                elif not run_before and resp.ok:
                    # Apscheduler won't have set a time by the first run so we set it here:
                    dump_file_time = datetime.now().replace(microsecond=0).isoformat()
                    current_time = dump_file_time.replace(":", "-")
                    run_before = True
                    headers_dump_file = (
                        dump_file_time.replace(":", "-")
                        + utc_offset
                        + name_seperator
                        + station_name
                        + "_metadata"
                        ".txt"
                    )
                    start_message = f"URL returned 200 OK. Saving {station_name} headers to: {headers_dump_file} and recording with content-type {resp.headers['content-type']} started at: {dump_file_time}{utc_offset} / {tz_name}."
                    headers_write = open(headers_dump_file, "w")
                    headers_write.write(
                        f"{start_message}\n \nHeaders file: {str(resp.headers)}"
                    )
                    headers_write.close()
                    print(start_message)
                if error_time:
                    # Don't set a datetime here.
                    # On resume it will continue writing to the filename as set by apscheduler.
                    # OR if it's the first successful run, it will get the date from not run_before above.
                    print(
                        f"{station_name} resumed recording after {str(datetime.now() - error_time).split('.')[0]}."
                    )
                    error_time = False
                async for chunk in resp.content.iter_chunked(chunk_size):
                    if not last_used_fn:
                        file_name = current_time + standard_file_name
                        write_file = open(file_name, "ab")
                        write_file.write(chunk)
                        last_used_fn = file_name
                        continue
                    # If apscheduler doesn't announce an incremented datetime then write the chunk to the already opened file.
                    elif current_time + standard_file_name == last_used_fn:
                        write_file.write(chunk)
                    # If apscheduler announces a new datetime then open that new file and begin writing to it.
                    else:
                        print(
                            f"New recording file for {station_name} is {current_time}."
                        )
                        write_file.close()
                        file_name = current_time + standard_file_name
                        write_file = open(file_name, "ab")
                        write_file.write(chunk)
                        last_used_fn = file_name
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            retry_attempts += 1
            # Aggressive attempt to reconnect on error.
            if retry_attempts < 5:
                sleep_time = random.randrange(1, 2)
            else:
                sleep_time = random.randrange(5, 30)
            error_time = datetime.now()


def run_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    if args_provided:
        loop.create_task(record_station(args.name, args.url))
    else:
        for key, value in dict_streams.items():
            url = value["url"]
            ext = value.get("ext")
            loop.create_task(record_station(key, url, ext))
    loop.run_forever()


if __name__ == "__main__":
    if args.directory:
        os.chdir(args.directory)
    else:
        os.chdir(save_to_directory)
    if args.url and args.name is None:
        parser.error("-u or --url  requires -n or --name")
    if args.name and args.url is None:
        parser.error("-n or --name requires -u or --url")
    if args.url and not args.url.startswith("http"):
        parser.error("URL must start with http")
    if args.name and args.url:
        args_provided = True
    ap_schedule = BackgroundScheduler()
    ap_schedule.add_job(update_time, trigger="cron", hour="*")
    ap_schedule.start()
    try:
        run_loop()
    except KeyboardInterrupt:
        sys.exit("Received keyboard interrupt, exiting.")
