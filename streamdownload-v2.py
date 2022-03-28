import asyncio
import aiohttp
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import sys
import random
import re

url = "http://frontend.stream.rawfm.net.au/i/syd-stream-192k.aac"
expected_content_type = "audio/*"
base_file_name = "raw_fm.aac"
name_seperator = "-"
chunk_size = int(1024)
last_used_fn = None
run_before = False
error_time = False
current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def update_time():
    global current_time
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    # Only announce creation of a new file if not stuck in an error.
    current_file = current_time + base_file_name
    if not error_time:
        print(
            f"Attempting to record to: {current_time + name_seperator + base_file_name}."
        )


async def record_station():
    global last_used_fn, error_time, run_before
    session = aiohttp.ClientSession()
    while True:
        try:
            async with session.get(url) as resp:
                if not re.match(expected_content_type, resp.headers["content-type"]):
                    sys.exit("Server's content-type is not audio. Check the link.")
                if not run_before and resp.status == 404:
                    sys.exit("URL is 404. Check the link.")
                elif not run_before and resp.ok:
                    headers_file = (
                        datetime.now().strftime("%Y-%m-%d-")
                        + base_file_name
                        + "-headers"
                        ".txt"
                    )
                    open(headers_file, "w").write(str(resp.headers))
                    # Apscheduler won't have set a time by the first run so we set it here:
                    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    print(
                        f"URL returned 200 OK. Saving headers to: {headers_file} and recording started at: {current_time}."
                    )
                    run_before = True
                if error_time:
                    # Don't set a date here.
                    # On resume it will continue writing to the filename as set by apschedule
                    # OR if it's the first successful run, it will get the date from not run_before above.
                    print(
                        f"Resumed recording after {str(datetime.now() - error_time).split('.')[0]}."
                    )
                    error_time = False
                async for chunk in resp.content.iter_chunked(chunk_size):
                    # Get the filename for the first run.
                    if not last_used_fn:
                        file_name = current_time + name_seperator + base_file_name
                        write_file = open(file_name, "ab")
                        write_file.write(chunk)
                        last_used_fn = file_name
                        continue
                    # If apscheduler doesn't announce an incremented filename then write the chunk to the already opened file.
                    elif current_time + name_seperator + base_file_name == last_used_fn:
                        write_file.write(chunk)
                    # If apscheduler announces a new filename then open that new file and begin writing to it.
                    else:
                        file_name = current_time + name_seperator + base_file_name
                        write_file = open(file_name, "ab")
                        write_file.write(chunk)
                        last_used_fn = file_name
        except OSError:
            pass
        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            sleep_time = "0"
            # if timeout < 1 second ignore timeout error? constant microsecond timeouts.
            sleep_time = random.randrange(5, 60)
            print(f"Could not connect to stream, retrying after {sleep_time} seconds.")
            print(datetime.now())
            print(e.__class__)
            error_time = datetime.now()
            await asyncio.sleep(sleep_time)


if __name__ == "__main__":
    ap_schedule = BackgroundScheduler()
    ap_schedule.add_job(update_time, trigger="cron", hour="*")
    ap_schedule.start()
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(record_station())
        loop.close()
    except KeyboardInterrupt:
        sys.exit("Received keyboard interrupt, exiting.")
