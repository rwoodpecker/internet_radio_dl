# stream_download

stream_download is a python tool that is used to internet download / archive internet radio streams and can be considered a modern replacement for [streamripper](http://streamripper.sourceforge.net/). It supports recording multiple streams at the same time.

## Basic usage:

1. pip install requirements.txt (it requires aiohttp and apscheduler)
2. Insert each stream you want to record into the dict_streams dictionary. An example is provided below:

```
dict_streams = {
    "raw_fm": "http://frontend.stream.rawfm.net.au/i/syd-stream-192k.aac",
    "claw_fm": "http://frontend.stream.rawfm.net.au/i/syd-stream-192k.aac",
}
```
3. run python stream_download.py, preferrably in screen or tmux if you intend to run it indefinitely.

## Technical notes

* Recordings will be split up and timestamped for the start of each hour:
  ```
  2022-03-29_10-00-00-raw_fm.aac
  2022-03-29_11-00-00-raw_fm.aac
  2022-03-29_12-00-00-raw_fm.aac
  ```
* On first succesful connection to the stream the first file will be timestamped for the time of connection, and then subsequent files will be timestamped each hour.
* You must supply a valid URL. On initial connection each URL will be checked for a valid HTTP response code and audio-type. Currently if there is an issue with either of these the script will exit to alert the user to check their URLs.
* This is an archival tool, as such it handles all disconnects or timeouts quickly. The script will agressively attempt to reconnect to the stream on error in a random range between 5 and 60 seconds.
* It is safe to interrupt this tool with Control + C, otherwise it will run and archive the streams forever.


## Todo 
1. Support custom file extensions where the stream URL does not have a file extension.
2. Implement argparse to specify stream URL and name so dict_streams can be provided as an argument and to prevent exiting the script if URL error is detected on first run (keep retrying URL instead).
3. Implement configuration file, move key config options to be user configurable including stream URLs, including timestamping of files, user agent, chunk size, directory, audio-type.
5. Implement metadata, such as basic tagging.
6. Implement maximum recording length.
8. Create pip release.
