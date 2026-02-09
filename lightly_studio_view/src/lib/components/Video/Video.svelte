<script lang="ts">
    import { PUBLIC_VIDEOS_FRAMES_MEDIA_URL, PUBLIC_VIDEOS_MEDIA_URL } from '$env/static/public';
    import type { FrameView, VideoFrameView, VideoView } from '$lib/api/lightly_studio_local';
    import { onMount } from 'svelte';

    interface VideoProps {
        video: VideoView;
        frames: FrameView[];
        update: (frame: FrameView | VideoFrameView | null, index: number | null) => void;
        videoEl: HTMLVideoElement | null;
        controls?: boolean;
        muted?: boolean;
        playsinline?: boolean;
        preload?: 'auto' | 'metadata' | 'none';
        className?: string;
        handleMouseEnter?: (event: MouseEvent) => void;
        handleMouseLeave?: (event: MouseEvent) => void;
        onplay?: () => void;
    }

    let {
        video,
        update,
        videoEl = $bindable(),
        frames = [],
        muted = true,
        playsinline = true,
        controls = false,
        preload = 'metadata',
        className = '',
        handleMouseEnter = () => {},
        handleMouseLeave = () => {},
        onplay = () => {}
    }: VideoProps = $props();

    let index = 0;

    let previousIndex: number | null = null;
    // error tolerance
    // TODO: Investigate if the EPS tolerance could cause
    // errors to obtain the correct frame
    const EPS = 0.002;

    onMount(() => {
        startFrameLoop();
    });

    function findFrame(currentTime: number): { frame: FrameView | VideoFrameView; index: number } {
        // move forward
        while (
            index < frames.length - 1 &&
            frames[index + 1].frame_timestamp_s <= currentTime + EPS
        ) {
            index++;
        }

        // move backwards
        while (
            index > 0 &&
            index < frames.length &&
            frames[index].frame_timestamp_s > currentTime + EPS
        ) {
            index--;
        }

        return { frame: frames[index], index };
    }

    function startFrameLoop() {
        function tick() {
            if (!videoEl) return;
            const { frame, index } = findFrame(videoEl.currentTime);

            if (previousIndex != index) {
                update(frame, index);
                previousIndex = index;
            }

            requestAnimationFrame(tick);
        }
        requestAnimationFrame(tick);
    }
</script>

<video
    bind:this={videoEl}
    src={`${PUBLIC_VIDEOS_MEDIA_URL}/${video.sample_id}`}
    {muted}
    {playsinline}
    {preload}
    {controls}
    class={className}
    onmouseenter={handleMouseEnter}
    onmouseleave={handleMouseLeave}
    {onplay}
    poster={frames.length > 0
        ? `${PUBLIC_VIDEOS_FRAMES_MEDIA_URL}/${frames[0].sample_id}?compressed=true`
        : null}
></video>
