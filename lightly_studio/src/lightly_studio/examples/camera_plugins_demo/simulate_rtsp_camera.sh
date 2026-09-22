#!/usr/bin/env bash
# Serve a video file as an RTSP camera, so the demo can run without hardware.
#
#   brew install mediamtx ffmpeg          # or your package manager
#   ./simulate_rtsp_camera.sh my_video.mp4
#
# The stream is then at rtsp://127.0.0.1:8554/cam
set -euo pipefail

VIDEO="${1:?usage: simulate_rtsp_camera.sh <video file> [path]}"
STREAM_PATH="${2:-cam}"

mediamtx "${MEDIAMTX_CONFIG:-/opt/homebrew/etc/mediamtx/mediamtx.yml}" &
MEDIAMTX_PID=$!
trap 'kill ${MEDIAMTX_PID} 2>/dev/null || true' EXIT
sleep 2

echo "Streaming ${VIDEO} to rtsp://127.0.0.1:8554/${STREAM_PATH}"
ffmpeg -v error -re -stream_loop -1 -i "${VIDEO}" \
  -an -c:v libx264 -preset ultrafast -tune zerolatency \
  -f rtsp "rtsp://127.0.0.1:8554/${STREAM_PATH}"
