<script lang="ts">
    import { PUBLIC_VIDEOS_MEDIA_URL } from '$env/static/public';
    import type { FrameView, VideoFrameView, VideoView } from '$lib/api/lightly_studio_local';

    export type AnyFrame = FrameView | VideoFrameView;

    interface VideoProps {
        video: VideoView;
        update: (frame: AnyFrame | null) => void;
        videoEl: HTMLVideoElement | null;
        controls?: boolean;
        muted?: boolean;
        playsinline?: boolean;
        preload?: 'auto' | 'metadata' | 'none';
        className?: string;
        handleMouseEnter?: (event: MouseEvent) => void;
        handleMouseLeave?: (event: MouseEvent) => void;
    }

    let {
        video,
        update,
        videoEl = $bindable(),
        muted = true,
        playsinline = true,
        controls = false,
        preload = 'metadata',
        className = '',
        handleMouseEnter = () => {},
        handleMouseLeave = () => {}
    }: VideoProps = $props();

    function onTimeUpdate(): AnyFrame | null {
        if (!video.frames || video.frames.length === 0 || !videoEl) return null;

        const currentTime = videoEl.currentTime;

        const pastFrames = video.frames.filter((f) => f.frame_timestamp_s <= currentTime);

        const frame =
            pastFrames.length > 0
                ? pastFrames.reduce((prev, curr) =>
                      curr.frame_timestamp_s > prev.frame_timestamp_s ? curr : prev
                  )
                : video.frames[0];

        update(frame);

        return frame;
    }
</script>

<video
    bind:this={videoEl}
    src={`${PUBLIC_VIDEOS_MEDIA_URL}/${video.sample_id}#t=0.001`}
    {muted}
    {playsinline}
    {preload}
    {controls}
    ontimeupdate={onTimeUpdate}
    class={className}
    onmouseenter={handleMouseEnter}
    onmouseleave={handleMouseLeave}
></video>
