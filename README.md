# internet_radio_dl

stream_download is a python tool that is used to download / archive internet radio streams and can be considered a modern replacement for [streamripper](http://streamripper.sourceforge.net/). It supports recording multiple streams at the same time.

## Basic usage:

1. pip install -r requirements.txt (it requires aiohttp and apscheduler)
2. Insert each stream you want to record into the dict_streams dictionary within the script. An example is provided below:

```
dict_streams = {
    "raw-fm": "http://frontend.stream.rawfm.net.au/i/syd-stream-192k.aac",
    "claw-fm": "http://frontend.stream.rawfm.net.au/i/syd-stream-192k.aac",
}
```

If you only want to record one stream or prefer not to use the dictionary you can pass the script a URL and station name to record.

For example: python internet_radio_dl.py --url http://frontend.stream.rawfm.net.au/i/syd-stream-192k.aac --name raw-fm

If using the --url command you must also specify the --name of the station.

By default the recordings are stored in your ~Downloads folder. This can be modified in the script or you can specify a folder by using the --directory argument on the command line. You don't need to pass the script a --url or --name on the command line for the --directory argument to be accepted. If no URL or station name is provided it will default to the those located in the script.

For all options see:
```
usage: internet_radio_dl.py [-h] [-u URL] [-n NAME] [-d DIRECTORY]

optional arguments:
  -h, --help            show this help message and exit
  -u URL, --url URL     url of stream
  -n NAME, --name NAME  shortname of stream e.g. raw_fm
  -d DIRECTORY, --directory DIRECTORY  directory to save files to
```

3. Run python internet_radio_dl.py, preferrably in screen or tmux if you intend to run it indefinitely.

For logging the output to a text file run as python -u internet_radio.py < any options> > station_name.log 

## Technical notes

* Recordings will be split up and timestamped for the start of each hour, in a general ISO 8601 format: YYYY-MM-DDTHH-MM-SS-UTC offset.
  ```
  2022-07-05T16-00-00+6000_raw-fm.aac
  2022-07-05T17-00-00+6000_raw-fm.aac
  2022-07-05T18-00-00+6000_raw-fm.aac
  ```

* You must supply valid URLs. On initial connection each URL will be checked for a valid HTTP response code and audio-type. Ideally the URL will end with a valid audio file extension such as .mp3 or .aac. If it doesn't the script will try to determine if from the URL. If there is an issue with the URLs the script will exit to alert the user to check them.
* On first succesful connection to the stream the file will be timestamped at the time of connection, and then subsequent files will be timestamped each hour.
* This is an archival tool, as such it handles all disconnects or timeouts quickly. The script will agressively attempt to reconnect to the stream on error in a random range between 5 and 60 seconds. For the first 5 reconnect attempts a random range of 2 to 5 seconds is used.
* The default user agent is Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36.
* There is a 5 second timeout on connecting and reading the audio stream.
* It is safe to keyboard interrupt (control + c ) this tool, otherwise it will run and archive the streams forever.