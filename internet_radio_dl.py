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
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36"
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

    station_names = set(dict_streams.keys())

    if args_provided:
        station_names.add(args.name)

    for station_name in station_names:
        stream_current_time[station_name] = new_time


def update_time_safe():
    loop.call_soon_threadsafe(update_time)


async def record_station(station_name, station_url, ext=None, sock_timeout=None):

    write_file = None
    last_used_fn = None
    last_used_stream_time = None

    first_time_attempts = 0
    retry_attempts = 0
    run_before = False

    error_time = None
    recovery_time = None

    cleanurl = station_url.rstrip("/")

    if sock_timeout is None:
        sock_timeout = 5

    timeout = aiohttp.ClientTimeout(total=None, sock_connect=5, sock_read=sock_timeout)

    if ext:
        file_extension = "." + ext.lstrip(".")
    else:
        file_extension = "." + cleanurl.split("/")[-1].split(".")[-1]

    last_flush_time = time.monotonic()

    try:
        while True:
            try:
                async with aiohttp.ClientSession(
                    timeout=timeout, headers=web_headers
                ) as session:

                    # Apply the existing network retry delay.
                    if error_time is not None:
                        print(
                            f"Could not connect to {station_name} at "
                            f"{datetime.now().replace(microsecond=0).isoformat()}, "
                            f"retrying after {sleep_time} seconds.\n"
                        )

                        await asyncio.sleep(sleep_time)

                    # Initial connection delay only.
                    # Subsequent failures use the existing retry logic above.
                    if not run_before and first_time_attempts == 0:
                        first_time_attempts += 1

                        print(
                            f"Attempting initial connection to {station_name}... "
                            f"attempt number #{first_time_attempts}.\n"
                        )

                        await asyncio.sleep(5)

                    async with session.get(station_url, timeout=timeout) as resp:

                        content_type = resp.headers.get("content-type", "")

                        # Validate every HTTP connection.
                        if resp.status == 404:
                            sys.exit("URL is 404. Check the link.")

                        if not resp.ok:
                            sys.exit(
                                f"HTTP error {resp.status} from {station_url}. "
                                f"Check the link or server."
                            )

                        if not content_type.startswith(expected_content_type):
                            sys.exit(
                                f"Server's content-type {content_type} "
                                f"is not audio. Check the URL."
                            )

                        # A valid HTTP connection has been established.
                        # Clear the pending retry delay so a subsequent
                        # clean EOF reconnects immediately.
                        if error_time is not None:
                            recovery_time = error_time
                            error_time = None

                        if not run_before:

                            if station_name not in stream_current_time:
                                dump_file_time = (
                                    datetime.now().replace(microsecond=0).isoformat()
                                )

                                stream_current_time[station_name] = (
                                    dump_file_time.replace(":", "-")
                                )

                            stream_time = stream_current_time[station_name]

                            run_before = True

                            # Current local timezone information.
                            local_now = datetime.now().astimezone()
                            utc_offset = local_now.strftime("%z")
                            tz_name = local_now.tzname()

                            headers_dump_file = (
                                stream_time
                                + utc_offset
                                + name_seperator
                                + station_name
                                + "_metadata.txt"
                            )

                            start_message = (
                                f"URL: {station_url} returned 200 OK.\n"
                                f"Saving {station_name} headers to: "
                                f"{headers_dump_file}.\n"
                                f"Recording {station_name} with content-type "
                                f"{content_type} started at: "
                                f"{stream_time}{utc_offset} / {tz_name}.\n"
                                f"Socket timeout is: {sock_timeout}.\n"
                                f"Recording location: {save_to_directory}."
                            )

                            with open(headers_dump_file, "w") as headers_write:
                                headers_write.write(
                                    f"{start_message}\n\nHeaders:\n"
                                    f"{dict(resp.headers)}"
                                )

                            print(start_message)

                        async for chunk in resp.content.iter_chunked(chunk_size):

                            # Actual audio reception resets the retry counter.
                            retry_attempts = 0

                            if recovery_time is not None:
                                print(
                                    f"{station_name} resumed recording after "
                                    f"{str(datetime.now() - recovery_time).split('.')[0]}.\n"
                                )

                                recovery_time = None

                            if station_name not in stream_current_time:
                                stream_current_time[station_name] = (
                                    datetime.now()
                                    .replace(microsecond=0)
                                    .isoformat()
                                    .replace(":", "-")
                                )

                            stream_time = stream_current_time[station_name]

                            # Reuse the existing filename when reconnecting
                            # within the same hourly recording period.
                            if (
                                stream_time == last_used_stream_time
                                and last_used_fn is not None
                            ):
                                file_name = last_used_fn

                            else:
                                # Refresh timezone information only when
                                # creating a new recording file.
                                local_now = datetime.now().astimezone()
                                utc_offset = local_now.strftime("%z")
                                tz_name = local_now.tzname()

                                standard_file_name = (
                                    utc_offset
                                    + name_seperator
                                    + station_name
                                    + file_extension
                                )

                                file_name = stream_time + standard_file_name

                            if write_file is None:

                                write_file = open(file_name, "ab")
                                write_file.write(chunk)

                                last_used_fn = file_name
                                last_used_stream_time = stream_time
                                last_flush_time = time.monotonic()

                                print(f"Started recording to: {file_name}.\n")

                            elif file_name == last_used_fn:

                                write_file.write(chunk)

                            else:

                                write_file.close()

                                write_file = open(file_name, "ab")
                                write_file.write(chunk)

                                last_used_fn = file_name
                                last_used_stream_time = stream_time
                                last_flush_time = time.monotonic()

                                print(
                                    f"New recording file for {station_name} "
                                    f"is: {file_name}."
                                )

                            # Flush periodically rather than every chunk.
                            if time.monotonic() - last_flush_time >= 30:
                                write_file.flush()
                                last_flush_time = time.monotonic()

                # Normal EOF:
                # Close the file and immediately reconnect.
                # No sleep or backoff is applied.
                if write_file is not None:
                    write_file.close()
                    write_file = None

            except (asyncio.TimeoutError, aiohttp.ClientError):

                # Close the current file before retrying.
                if write_file is not None:
                    write_file.close()
                    write_file = None

                retry_attempts += 1

                if retry_attempts < 5:
                    sleep_time = round(random.uniform(0.1, 1))
                else:
                    sleep_time = random.randrange(1, 5)

                if error_time is None:
                    error_time = datetime.now()

    except asyncio.CancelledError:

        print(f"[INFO] Recording stopped for {station_name}.")

        raise

    except OSError as e:

        print(
            f"[ERROR] File or filesystem error for {station_name}: "
            f"{e}. Stopping this recording task."
        )

    finally:

        if write_file is not None:
            try:
                write_file.close()
            except OSError as e:
                print(
                    f"[WARNING] Could not close recording file for "
                    f"{station_name}: {e}"
                )

        print(f"[INFO] File cleanup completed for {station_name}.")


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
        parser.error("-u or --url requires -n or --name")

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

        print("\n[INFO] KeyboardInterrupt received. " "Stopping ALL tasks...")

    finally:

        tasks = asyncio.all_tasks(loop)

        for task in tasks:
            task.cancel()

        loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))

        ap_schedule.shutdown(wait=False)

        loop.close()

        print("[INFO] All tasks and scheduler shut down. Exiting.")
