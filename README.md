# internet_radio_dl

stream_download is a python tool that is used to download / archive internet radio streams and can be considered a modern replacement for [streamripper](http://streamripper.sourceforge.net/). It supports recording multiple streams at the same time.

## Basic usage:

1. pip install requirements.txt (it requires aiohttp and apscheduler)
2. Insert each stream you want to record into the dict_streams dictionary. An example is provided below:

```
dict_streams = {
    "raw_fm": "http://frontend.stream.rawfm.net.au/i/syd-stream-192k.aac",
    "claw_fm": "http://frontend.stream.rawfm.net.au/i/syd-stream-192k.aac",
}
```

If you only want to record one stream or prefer not to use a dictionary you can pass the script a URL and station name to record.

For example: python internet_radio_dl.py --url http://frontend.stream.rawfm.net.au/i/syd-stream-192k.aac --name raw_fm

or

python internet_radio_dl.py -u http://frontend.stream.rawfm.net.au/i/syd-stream-192k.aac -n raw_fm

```
usage: internet_radio_dl.py [-h] [-u URL] [-n NAME]

optional arguments:
-h, --help            show this help message and exit
-u URL, --url URL     url of stream
-n NAME, --name NAME  shortname of stream e.g. raw_fm
```

3. Run python internet_radio_dl.py, preferrably in screen or tmux if you intend to run it indefinitely.

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
* It is safe to keyboard interrupt (control +c ) this tool, otherwise it will run and archive the streams forever.
