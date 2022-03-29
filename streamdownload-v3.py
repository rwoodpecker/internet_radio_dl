import asyncio
import aiohttp
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import sys
import random
import re

dict_streams = {
    "raw_fm": "http://frontend.stream.rawfm.net.au/i/syd-stream-192k.aac",
    "claw_fm": "http://frontend.stream.rawfm.net.au/i/syd-stream-192k.aac",
}

expected_content_type = "audio/*"
name_seperator = "-"
web_headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; rv:98.0) Gecko/20100101 Firefox/98.0"
}
chunk_size = 1024


def update_time():
    global current_time
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


async def record_station(station_name, station_url):
    global current_time
    last_used_fn = None
    first_time_attempts = 0
    retry_attempts = 0
    run_before = False
    error_time = False
    file_extension = station_url[-4:]
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
                    f"Attempting initial connection to {station_name}... Attempt number #{first_time_attempts}."
                )
                if first_time_attempts < 2:
                    await asyncio.sleep(5)
                else:
                    await asyncio.sleep(random.randrange(5, 60))
            async with session.get(
                station_url,
                timeout=aiohttp.ClientTimeout(total=None, sock_connect=5, sock_read=5),
                headers=web_headers,
            ) as resp:
                retry_attempts = 0
                if not re.match(expected_content_type, resp.headers["content-type"]):
                    sys.exit("Server's content-type is not audio. Check the link.")
                if not run_before and resp.status == 404:
                    sys.exit("URL is 404. Check the link.")
                elif not run_before and resp.ok:
                    headers_dump_file = (
                        datetime.now().strftime("%Y-%m-%d-") + station_name + "-headers"
                        ".txt"
                    )
                    open(headers_dump_file, "w").write(str(resp.headers))
                    # Apscheduler won't have set a time by the first run so we set it here:
                    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    run_before = True
                    print(
                        f"URL returned 200 OK. Saving {station_name} headers to: {headers_dump_file} and recording with content-type {resp.headers['content-type']} started at: {current_time}."
                    )
                if error_time:
                    # Don't set a date here.
                    # On resume it will continue writing to the filename as set by apschedule
                    # OR if it's the first successful run, it will get the date from not run_before above.
                    print(
                        f"{station_name} resumed recording after {str(datetime.now() - error_time).split('.')[0]}."
                    )
                    error_time = False
                async for chunk in resp.content.iter_chunked(chunk_size):
                    # increase chunk size bigger and check last time since chunk size, if >60 seconds, re-start.
                    # print(f"chunk size is {sys.getsizeof(chunk)}")
                    # Get the filename for the first run.
                    if not last_used_fn:
                        file_name = (
                            current_time
                            + name_seperator
                            + station_name
                            + file_extension
                        )
                        write_file = open(file_name, "ab")
                        write_file.write(chunk)
                        last_used_fn = file_name
                        continue
                    # If apscheduler doesn't announce an incremented filename then write the chunk to the already opened file.
                    elif (
                        current_time + name_seperator + station_name + file_extension
                        == last_used_fn
                    ):
                        write_file.write(chunk)
                    # If apscheduler announces a new filename then open that new file and begin writing to it.
                    else:
                        print(
                            f"New recording file for {station_name} is {current_time}."
                        )
                        file_name = (
                            current_time
                            + name_seperator
                            + station_name
                            + file_extension
                        )
                        write_file = open(file_name, "ab")
                        write_file.write(chunk)
                        last_used_fn = file_name
        except OSError:
            pass
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            sleep_time = random.randrange(5, 60)
            error_time = datetime.now()
            retry_attempts += 1


def run_loop():
    loop = asyncio.get_event_loop()
    for key, value in dict_streams.items():
        loop.create_task(record_station(key, value))
    loop.run_forever()


if __name__ == "__main__":
    ap_schedule = BackgroundScheduler()
    ap_schedule.add_job(update_time, trigger="cron", hour="*")
    ap_schedule.start()
    try:
        run_loop()
    except KeyboardInterrupt:
        sys.exit("Received keyboard interrupt, exiting.")
