#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "usage: $0 <video-file>" >&2
    exit 1
fi

mkdir -p ./static

shopt -s nullglob
old_files=(./static/*.m3u8 ./static/*.ts ./static/*.vtt ./static/*.tmp)
if ((${#old_files[@]})); then
    rm -f "${old_files[@]}"
fi

audio_streams="$(ffprobe -v error -select_streams a \
    -show_entries stream=index:stream_tags=language \
    -of csv=p=0 "$1" 2>/dev/null || true)"
audio_map="0:a:0?"
audio_index="$(awk -F, 'tolower($2) ~ /^(eng|en)([_-].*)?$/ {print $1; exit}' <<<"$audio_streams")"
if [ -n "$audio_index" ]; then
    audio_map="0:$audio_index"
fi

run_id="$(date +%s)-$$"

exec ffmpeg -hide_banner -loglevel warning -nostdin -y \
    -re -i "$1" \
    -map 0:V:0 -map "$audio_map" -sn \
    -c:v libx264 -preset fast -b:v 3000k -maxrate 3000k -bufsize 6000k \
    -pix_fmt yuv420p -force_key_frames "expr:gte(t,n_forced*4)" -sc_threshold 0 \
    -c:a aac -b:a 128k -ac 2 \
    -f hls -hls_time 4 -hls_list_size 40 -hls_delete_threshold 3 \
    -hls_flags delete_segments+independent_segments+temp_file \
    -hls_segment_filename "./static/seg_${run_id}_%05d.ts" \
    ./static/output.m3u8
