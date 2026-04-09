# YouTube-VOS demo assets

Place files here for the overlay demo:

- `base.mp4`: RGB video rendered from one YouTube-VOS sequence
- `overlay-mask.mp4`: mask/annotation overlay video rendered from matching annotation frames

The HTML demo reads these files from:

- `/examples/assets/ytvos/base.mp4`
- `/examples/assets/ytvos/overlay-mask.mp4`

Generate files from `youtube_vis_50_videos`:

```bash
python3 scripts/generate_youtube_vis_overlay.py --list-videos
python3 scripts/generate_youtube_vis_overlay.py --video-name 0a23765d15
python3 scripts/generate_youtube_vis_overlay.py --video-name 0a23765d15 --render-mode both
```

`--render-mode`:
- `bbox`: bounding-box overlay to `overlay-mask.mp4`
- `mask`: segmentation-mask overlay to `overlay-mask.mp4`
- `both`: bbox to `overlay-mask.mp4` and mask to `overlay-segmentation-mask.mp4`
