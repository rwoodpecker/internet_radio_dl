import asyncio
import aiohttp
import datetime
import os
from apscheduler.schedulers.blocking import BlockingScheduler

chunked = int(1024)
file_open = False


def update_time():
    current_time = datetime.now()


async def main():
    url = "http://frontend.stream.rawfm.net.au/i/syd-stream-192k.aac"
    first_time = True
    session = aiohttp.ClientSession()
    async with session.get(url) as resp:
        async for chunk in resp.content.iter_chunked(chunked):
            if first_time:
                latest_file_time = datetime.datetime.now()
                file_name = open(
                    latest_file_time.strftime("%H_%M") + "-raw_fm" + ".aac", "ab"
                )
                file_name.write(chunk)
                first_time = False

            if datetime.datetime.now() > latest_file_time:
                latest_file_time_check = datetime.datetime.now()
                checktime = True
                file_name = open(
                    latest_file_time_check.strftime("%H_%M") + "-raw_fm" + ".aac", "ab"
                )
                file_name.write(chunk)

            # latest_file_time = datetime.datetime.now()
            # if first_time:
            #     latest_file_time = datetime.datetime.now()
            #     file_name = open(
            #         latest_file_time.strftime("%H_%M") + "-raw_fm" + ".aac", "ab"
            #     )
            #     file_name.write(chunk)
            #     first_time = False

            # if not first_time and not "checktime" in locals():
            #     latest_file_time_check = datetime.datetime.now()
            #     file_name = open(
            #         latest_file_time_check.strftime("%H_%M") + "-raw_fm" + ".aac", "ab"
            #     )
            #     file_name.write(chunk)

            # if datetime.datetime.now() > latest_file_time_check:
            #     latest_file_time_check = datetime.datetime.now()
            #     checktime = True
            #     file_name = open(
            #         latest_file_time_check.strftime("%H_%M") + "-raw_fm" + ".aac", "ab"
            #     )
            #     file_name.write(chunk)


# await session.close()


if __name__ == "__main__":
    asyncio.run(main())
