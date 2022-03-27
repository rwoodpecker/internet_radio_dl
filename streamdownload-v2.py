import asyncio
from time import sleep
import aiohttp
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import sys
import random
import logging

url = "http://frontend.stream.rawfm.net.au/i/syd-stream-192k.aac"
base_file_name = "-raw_fm.aac"
current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
chunk_size = int(1024)
last_used_fn = None
run_before = False
error_time = False


def update_time():
    global current_time
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    # if stream.statusprint(f"Creating new recording file at {current_time}")


# async def function to check URL on first visit https://stackoverflow.com/questions/50577117/how-to-check-url-status-code-using-aiohttp & https://stackoverflow.com/questions/41398596/two-independent-async-loops-in-python


async def record_station():
    url = "http://frontend.stream.rawfm.net.au/i/syd-stream-192k.aac"
    logging.getLogger("asyncio").setLevel(logging.CRITICAL)
    global last_used_fn, session, error_time, run_before
    session = aiohttp.ClientSession()
    # put this in a while true and call loop externally? https://stackoverflow.com/questions/55971194/restart-asyncio-loop-in-exception
    while True:
        try:
            async with session.get(url) as resp:
                if not run_before and resp.ok:
                    print("URL returned 200 OK")
                    run_before = True
                if error_time:
                    print(
                        f"Resumed recording after {str((datetime.now() - error_time)).split('.')[0]}"
                    )
                    error_time = False

                async for chunk in resp.content.iter_chunked(chunk_size):
                    # Get the filename for the first run.
                    if not last_used_fn:
                        file_name = current_time + base_file_name
                        write_file = open(file_name, "ab")
                        write_file.write(chunk)
                        last_used_fn = file_name
                        continue
                    # If apscheduler doesn't announce an incremented filename then only write the chunk to the already opened file.
                    elif current_time + base_file_name == last_used_fn:
                        write_file.write(chunk)
                    # If apscheduler announces a new filename then open that new file and begin writing to it.
                    else:
                        file_name = current_time + base_file_name
                        write_file = open(file_name, "ab")
                        write_file.write(chunk)
                        last_used_fn = file_name
        except KeyboardInterrupt:
            sys.exit("Exiting.")
        except (asyncio.TimeoutError, aiohttp.ClientError):
            sleep_time = random.randrange(5, 10)
        print(f"Could not connect to stream, retrying after {sleep_time} seconds.")
        error_time = datetime.now()
        await asyncio.sleep(sleep_time)


if __name__ == "__main__":
    ap_schedule = BackgroundScheduler()
    ap_schedule.add_job(update_time, trigger="cron", hour="*", minute="*/1")
    ap_schedule.start()

    print(f"Starting the scheduler recording at {current_time}")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(record_station())
    loop.close()

    # while True:
    #     try:
    #         asyncio.run(main())
    #     except KeyboardInterrupt:
    #         sys.exit("Exiting.")
    #     except (asyncio.TimeoutError, aiohttp.ClientError):
    #         sleep_time = random.randrange(5, 10)
    #         print(f"Could not connect to stream, retrying after {sleep_time} seconds.")
    #         error_time = datetime.now()
    #         sleep(sleep_time)
