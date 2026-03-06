<script lang="ts">
    import { PUBLIC_VIDEOS_FRAMES_MEDIA_URL, PUBLIC_VIDEOS_MEDIA_URL } from '$env/static/public';
    import type { FrameView, VideoFrameView, VideoView } from '$lib/api/lightly_studio_local';
    import { findFrame } from '$lib/utils/frame';
    import { onDestroy, onMount } from 'svelte';

    interface VideoProps {
        video: VideoView;
        frames: FrameView[];
        update: (frame: FrameView | VideoFrameView | null, index: number | null) => void;
        videoEl: HTMLVideoElement | null;
        controls?: boolean;
        muted?: boolean;
        playsinline?: boolean;
        preload?: 'auto' | 'metadata' | 'none';
        active?: boolean;
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
        active = true,
        className = '',
        handleMouseEnter = () => {},
        handleMouseLeave = () => {},
        onplay = () => {},
        onseeked = () => {}
    }: VideoProps = $props();

    let previousIndex: number | null = null;
    let frameLoopId: number | null = null;

    onMount(() => {
        startFrameLoop();
    });

    onDestroy(() => {
        if (frameLoopId !== null) {
            cancelAnimationFrame(frameLoopId);
        }
    });

    $effect(() => {
        if (active || !videoEl) return;

        videoEl.pause();
        videoEl.removeAttribute('src');
        videoEl.load();
    });

    function startFrameLoop() {
        function tick() {
            if (!videoEl) return;
            const { frame, index } = findFrame({ frames, currentTime: videoEl.currentTime });

            if (index !== null && previousIndex !== index) {
                update(frame, index);
                previousIndex = index;
            }

            frameLoopId = requestAnimationFrame(tick);
        }
        frameLoopId = requestAnimationFrame(tick);
    }

    function handlePlay() {
        onplay();
    }

    function handleSeeked(event: Event) {
        onseeked(event);
    }
</script>

<video
    bind:this={videoEl}
    src={active ? `${PUBLIC_VIDEOS_MEDIA_URL}/${video.sample_id}` : undefined}
    {muted}
    {playsinline}
    {preload}
    {controls}
    class={className}
    onmouseenter={handleMouseEnter}
    onmouseleave={handleMouseLeave}
    onplay={handlePlay}
    onseeked={handleSeeked}
    poster={frames.length > 0
        ? `${PUBLIC_VIDEOS_FRAMES_MEDIA_URL}/${frames[0].sample_id}?compressed=true`
        : null}
></video>
