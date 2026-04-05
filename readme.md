App that allow u stream some kind of series or movies.

How to use?
Install ffmpeg: `sudo apt install ffmpeg`
Create file "history"
Put there path to ur first series u wanna to watch.

ex:
`echo "/abs/path/to/series" > history`

Run next commands:

`python main.py & python run_series.py`
sudo docker run --volume /home/evgenchic174/python_scripts/stream_platform/videos/:/app/videos -p 5000:5000 stream_platform
sudo docker run --volume "`pwd`/videos/:/app/videos" -p 5000:5000 stream_platform
sudo docker run --volume /home/evgenchic174/python_scripts/stream_platform/videos/:/app/videos --volume /home/evgenchic174/python_scripts/stream_platform/history:/app/history -p 5000:5000 stream_platform
