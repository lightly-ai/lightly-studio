<script lang="ts">
    import { PUBLIC_VIDEOS_FRAMES_MEDIA_URL, PUBLIC_VIDEOS_MEDIA_URL } from '$env/static/public';
    import type { FrameView, VideoFrameView, VideoView } from '$lib/api/lightly_studio_local';
    import { findFrame } from '$lib/utils/frame';
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
        onseeked?: (event: Event) => void;
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
        onplay = () => {},
        onseeked = () => {}
    }: VideoProps = $props();

    let previousIndex: number | null = null;

    onMount(() => {
        startFrameLoop();
    });

    function startFrameLoop() {
        function tick() {
            if (!videoEl) return;
            const { frame, index } = findFrame({ frames, currentTime: videoEl.currentTime });

            if (index !== null && previousIndex !== index) {
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
    {onseeked}
    poster={frames.length > 0
        ? `${PUBLIC_VIDEOS_FRAMES_MEDIA_URL}/${frames[0].sample_id}?compressed=true`
        : null}
></video>
