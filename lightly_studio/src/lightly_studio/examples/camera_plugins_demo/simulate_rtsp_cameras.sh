#!/usr/bin/env bash
# Serve every video file in a directory as its own RTSP camera.
#
#   brew install mediamtx ffmpeg          # or your package manager
#   ./simulate_rtsp_cameras.sh ~/demo_data/cameras
#
# A file named pool.mp4 becomes rtsp://127.0.0.1:8554/pool. Each stream plays in a
# loop. Type another URL in the source field of the Camera Station to change camera.
set -euo pipefail

DIRECTORY="${1:?usage: simulate_rtsp_cameras.sh <directory with video files>}"
CONFIG="${MEDIAMTX_CONFIG:-/opt/homebrew/etc/mediamtx/mediamtx.yml}"

mediamtx "${CONFIG}" &
PIDS=($!)
sleep 2

for video in "${DIRECTORY}"/*.mp4; do
  name="$(basename "${video}" .mp4)"
  ffmpeg -v error -re -stream_loop -1 -i "${video}" \
    -an -c:v libx264 -preset ultrafast -tune zerolatency \
    -f rtsp "rtsp://127.0.0.1:8554/${name}" &
  PIDS+=($!)
  echo "rtsp://127.0.0.1:8554/${name}"
done

trap 'kill "${PIDS[@]}" 2>/dev/null || true' EXIT
echo "Press Ctrl+C to stop all cameras."
wait
