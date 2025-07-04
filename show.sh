echo $1 
echo `pwd`
ffmpeg -re -i "$1" \
       	-map 0:a:m:language:eng -map 0:v \
       	-c:v libx264 -preset fast -b:v 3000k -maxrate 3000k -bufsize 6000k -c:a aac -b:a 128k \
	-f hls -hls_time 4 -hls_list_size 40 -hls_delete_threshold 3 -hls_flags delete_segments \
	./static/output.m3u8
