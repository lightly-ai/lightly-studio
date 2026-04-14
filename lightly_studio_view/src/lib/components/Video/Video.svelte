<script lang="ts">
    import { PUBLIC_VIDEOS_FRAMES_MEDIA_URL, PUBLIC_VIDEOS_MEDIA_URL } from '$env/static/public';
    import type { FrameView, VideoView } from '$lib/api/lightly_studio_local';
    import { getGridFrameURL, getGridThumbnailRequestSize } from '$lib/utils';

    interface VideoProps {
        video: VideoView;
        frames: FrameView[];
        videoEl: HTMLVideoElement | null;
        controls?: boolean;
        muted?: boolean;
        playsinline?: boolean;
        preload?: 'auto' | 'metadata' | 'none';
        className?: string;
        posterSize?: number;
        handleMouseEnter?: (event: MouseEvent) => void;
        handleMouseLeave?: (event: MouseEvent) => void;
        onplay?: () => void;
        onseeked?: (event: Event) => void;
    }

    let {
        video,
        videoEl = $bindable(),
        frames = [],
        muted = true,
        playsinline = true,
        controls = false,
        preload = 'metadata',
        className = '',
        posterSize,
        handleMouseEnter = () => {},
        handleMouseLeave = () => {},
        onplay = () => {},
        onseeked = () => {}
    }: VideoProps = $props();

    let previousVideoSampleId: string | null = null;
    let sourceLoadError = $state<string | null>(null);

    // HTMLMediaElement.error.code values.
    const MEDIA_ERROR_MESSAGES: Record<number, string> = {
        1: 'Video loading was canceled.',
        2: 'Network error while loading the video.',
        3: 'Video decoding failed.',
        4: 'Video source is unavailable or unsupported.'
    };
    const posterUrl = $derived.by(() => {
        if (frames.length === 0) {
            return null;
        }

        if (!posterSize) {
            return `${PUBLIC_VIDEOS_FRAMES_MEDIA_URL}/${frames[0].sample_id}`;
        }

        const requestedSize = getGridThumbnailRequestSize(
            posterSize,
            globalThis.window?.devicePixelRatio || 1
        );
        // Always use high quality (JPEG) for grid posters to maintain performance.
        return getGridFrameURL({
            sampleId: frames[0].sample_id,
            quality: 'high',
            renderedWidth: requestedSize,
            renderedHeight: requestedSize
        });
    });

    function handleVideoError() {
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
            videoEl.pause();
            videoEl.removeAttribute('src');
            videoEl.load();
        }

        sourceLoadError = null;
        videoEl.src = `${PUBLIC_VIDEOS_MEDIA_URL}/${currentVideoSampleId}`;
        previousVideoSampleId = currentVideoSampleId;
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
        poster={posterUrl}
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
