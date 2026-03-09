<script lang="ts">
    import { PUBLIC_VIDEOS_FRAMES_MEDIA_URL, PUBLIC_VIDEOS_MEDIA_URL } from '$env/static/public';
    import type { FrameView, VideoFrameView, VideoView } from '$lib/api/lightly_studio_local';
    import { findFrame } from '$lib/utils/frame';

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
    let frameRequestId: number | null = null;
    let previousVideoSampleId: string | null = null;
    let sourceLoadError = $state<string | null>(null);

    // HTMLMediaElement.error.code values.
    const MEDIA_ERROR_MESSAGES: Record<number, string> = {
        1: 'Video loading was canceled.',
        2: 'Network error while loading the video.',
        3: 'Video decoding failed.',
        4: 'Video source is unavailable or unsupported.'
    };

    function startFrameLoop() {
        clearFrameLoop();

        function tick() {
            if (!videoEl) {
                frameRequestId = null;
                return;
            }
            const { frame, index } = findFrame({ frames, currentTime: videoEl.currentTime });

            if (index !== null && previousIndex !== index) {
                update(frame, index);
                previousIndex = index;
            }

            frameRequestId = requestAnimationFrame(tick);
        }

        frameRequestId = requestAnimationFrame(tick);
    }

    function clearFrameLoop() {
        if (frameRequestId !== null) {
            cancelAnimationFrame(frameRequestId);
            frameRequestId = null;
        }
    }

    function handleVideoError() {
        clearFrameLoop();
        previousIndex = null;
        const errorCode = videoEl?.error?.code;
        sourceLoadError =
            (errorCode != null ? MEDIA_ERROR_MESSAGES[errorCode] : null) ??
            'Failed to load video source.';
    }

    function handleVideoLoadedData() {
        sourceLoadError = null;
    }

    $effect(() => {
        if (!videoEl) return;

        const currentVideoSampleId = video.sample_id;

        if (previousVideoSampleId !== null && previousVideoSampleId !== currentVideoSampleId) {
            previousIndex = null;
            videoEl.pause();
            videoEl.removeAttribute('src');
            videoEl.load();
        }

        sourceLoadError = null;
        videoEl.src = `${PUBLIC_VIDEOS_MEDIA_URL}/${currentVideoSampleId}`;
        previousVideoSampleId = currentVideoSampleId;
        startFrameLoop();

        return () => {
            clearFrameLoop();
        };
    });
</script>

<div class="relative h-full w-full">
    <video
        bind:this={videoEl}
        {muted}
        {playsinline}
        {preload}
        {controls}
        class={className}
        onmouseenter={handleMouseEnter}
        onmouseleave={handleMouseLeave}
        {onplay}
        {onseeked}
        onerror={handleVideoError}
        onloadeddata={handleVideoLoadedData}
        poster={frames.length > 0
            ? `${PUBLIC_VIDEOS_FRAMES_MEDIA_URL}/${frames[0].sample_id}?compressed=true`
            : null}
    ></video>
    {#if sourceLoadError}
        <div
            role="status"
            aria-live="polite"
            class="absolute inset-0 z-[10] flex items-center justify-center bg-black/70 p-2 text-center text-xs font-medium text-white"
        >
            {sourceLoadError}
        </div>
    {/if}
</div>
