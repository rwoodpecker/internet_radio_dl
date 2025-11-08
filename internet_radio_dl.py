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
    "groove-1": {
        "url": "https://ice2.somafm.com/groovesalad-128-aac",
        "ext": "aac",
        "sock_timeout": 20,
    },
    "groove-2": {
        "url": "https://ice2.somafm.com/groovesalad-128-aac",
        "ext": None,
        "sock_timeout": None,
    },
    # example of no extension or sock_timeout being defined
}

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
expected_content_type = "audio/"
name_seperator = "_"
web_headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
}
chunk_size = 2048
stream_current_time = {}

parser = argparse.ArgumentParser()
parser.add_argument("-u", "--url", type=str, help="url of stream")
parser.add_argument("-n", "--name", type=str, help="shortname of stream e.g. raw_fm")
parser.add_argument("-d", "--directory", type=str, help="directory to save files to")
args = parser.parse_args()
args_provided = False


def update_time():
    global stream_current_time
    new_time = (
        datetime.now().replace(second=0, microsecond=0).isoformat().replace(":", "-")
    )
    for station_name in dict_streams.keys():
        stream_current_time[station_name] = new_time


def update_time_safe():
    loop.call_soon_threadsafe(update_time)


async def record_station(station_name, station_url, ext=None, sock_timeout=None):
    last_used_fn = None
    first_time_attempts = 0
    retry_attempts = 0
    run_before = False
    error_time = None
    utc_offset = time.strftime("%z")
    tz_name = datetime.now().astimezone().tzname()
    cleanurl = station_url.rstrip("/")
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=5, sock_read=sock_timeout)

    if ext:
        file_extension = "." + ext.lstrip(".")
    else:
        file_extension = "." + cleanurl.split("/")[-1].split(".")[-1]
    standard_file_name = utc_offset + name_seperator + station_name + file_extension

    if sock_timeout is None:
        sock_timeout = 5

    while True:
        try:
            async with aiohttp.ClientSession(
                timeout=timeout, headers=web_headers
            ) as session:
                if error_time is not None:
                    print(
                        f"Could not connect to {station_name} stream, retrying after {sleep_time} seconds.\n"
                    )
                    await asyncio.sleep(sleep_time)

                if not run_before:
                    first_time_attempts += 1
                    print(
                        f"Attempting initial connection to {station_name}... attempt number #{first_time_attempts}.\n"
                    )
                    if first_time_attempts < 2:
                        await asyncio.sleep(5)
                    else:
                        await asyncio.sleep(random.randrange(5, 60))

                async with session.get(station_url, timeout=timeout) as resp:
                    retry_attempts = 0
                    content_type = resp.headers.get("content-type", "")
                    if not run_before and content_type.startswith(expected_content_type):
                        sys.exit(
                            f"Server's content‑type {resp.headers.get('content-type')} is not audio. Check the URL."
                        )
                    if not run_before and resp.status == 404:
                        sys.exit("URL is 404. Check the link.")
                    elif not run_before and resp.ok:
                        if station_name not in stream_current_time:
                            dump_file_time = (
                                datetime.now().replace(microsecond=0).isoformat()
                            )
                            stream_current_time[station_name] = dump_file_time.replace(
                                ":", "-"
                            )
                        stream_time = stream_current_time[station_name]
                        run_before = True
                        headers_dump_file = (
                            stream_time
                            + utc_offset
                            + name_seperator
                            + station_name
                            + "_metadata.txt"
                        )
                        start_message = (
                            f"URL: {station_url} returned 200 OK.\n"
                            f"Saving {station_name} headers to: {headers_dump_file}.\n"
                            f"Recording {station_name} with content‑type {resp.headers['content-type']} started at: "
                            f"{stream_time}{utc_offset} / {tz_name}.\n"
                            f"Socket timeout is: {sock_timeout}.\nRecording location: {save_to_directory}."
                        )
                        with open(headers_dump_file, "w") as headers_write:
                            headers_write.write(
                                f"{start_message}\n\nHeaders:\n{dict(resp.headers)}"
                            )
                        print(start_message)
                    async for chunk in resp.content.iter_chunked(chunk_size):
                        if error_time is not None:
                            print(
                                f"{station_name} resumed recording after {str(datetime.now() - error_time).split('.')[0]}.\n"
                            )
                            error_time = None
                        if station_name not in stream_current_time:
                            stream_current_time[station_name] = (
                                datetime.now()
                                .replace(microsecond=0)
                                .isoformat()
                                .replace(":", "-")
                            )
                        file_name = (
                            stream_current_time[station_name] + standard_file_name
                        )
                        if not last_used_fn:
                            write_file = open(file_name, "ab")
                            write_file.write(chunk)
                            last_used_fn = file_name
                            print(f"Started recording to: {file_name}.\n")
                        elif file_name == last_used_fn:
                            write_file.write(chunk)
                        else:
                            write_file.close()
                            write_file = open(file_name, "ab")
                            write_file.write(chunk)
                            last_used_fn = file_name
                            print(
                                f"New recording file for {station_name} is: {file_name}."
                            )
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            retry_attempts += 1
            if retry_attempts < 60:
                sleep_time = random.randrange(1, 2)
            else:
                sleep_time = random.randrange(5, 30)
            if error_time is None:
                error_time = datetime.now()
        except asyncio.CancelledError:
            write_file.close()
            print(f"[INFO] Recording stopped for {station_name}. File closed safely.")
            raise


def run_loop():
    if args_provided:
        loop.create_task(record_station(args.name, args.url))
    else:
        for key, value in dict_streams.items():
            url = value["url"]
            ext = value.get("ext")
            sock_timeout = value.get("sock_timeout")
            loop.create_task(record_station(key, url, ext, sock_timeout))
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
    ap_schedule.add_job(update_time_safe, trigger="cron", hour="*")
    ap_schedule.start()
    try:
        run_loop()
    except KeyboardInterrupt:
        print("\n[INFO] KeyboardInterrupt received. Stopping ALL tasks...")
    finally:
        tasks = asyncio.all_tasks(loop)
        for task in tasks:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        ap_schedule.shutdown(wait=False)
        loop.close()
        print("[INFO] All tasks and scheduler shut down. Exiting.")
