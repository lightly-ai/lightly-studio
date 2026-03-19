<script lang="ts">
    interface VideoPlayerProps {
        src: string;
        controls?: boolean;
        muted?: boolean;
        playsinline?: boolean;
        preload?: 'auto' | 'metadata' | 'none';
        className?: string;
        handleMouseEnter?: (event: MouseEvent) => void;
        handleMouseLeave?: (event: MouseEvent) => void;
        onplay?: () => void;
        width?: number;
        height?: number;
        videoEl?: HTMLVideoElement | null;
        playbackTime?: number;
    }

    let {
        src,
        muted = true,
        playsinline = true,
        controls = false,
        preload = 'metadata',
        className = '',
        handleMouseEnter = () => {},
        handleMouseLeave = () => {},
        onplay = () => {},
        width = $bindable(0),
        height = $bindable(0),
        videoEl = $bindable(null),
        playbackTime = $bindable(0)
    }: VideoPlayerProps = $props();

    let previousSrc: string | null = null;
    let sourceLoadError = $state<string | null>(null);
    let isHovered = $state(false);

    // HTMLMediaElement.error.code values.
    const MEDIA_ERROR_MESSAGES: Record<number, string> = {
        1: 'Video loading was canceled.',
        2: 'Network error while loading the video.',
        3: 'Video decoding failed.',
        4: 'Video source is unavailable or unsupported.'
    };

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

        if (previousSrc !== null && previousSrc !== src) {
            videoEl.pause();
            videoEl.removeAttribute('src');
            videoEl.load();
        }

        sourceLoadError = null;
        videoEl.src = src;
        previousSrc = src;
    });

    // Track video element size and expose it via bindable props
    $effect(() => {
        if (!videoEl) return;

        const updateSize = () => {
            const rect = videoEl?.getBoundingClientRect();
            width = rect?.width ?? 0;
            height = rect?.height ?? 0;
        };

        updateSize();

        const resizeObserver = new ResizeObserver(updateSize);
        resizeObserver.observe(videoEl);

        return () => resizeObserver.disconnect();
    });

    // Track playback time
    $effect(() => {
        if (!videoEl) return;

        const handleTimeUpdate = () => {
            playbackTime = videoEl?.currentTime ?? 0;
        };

        videoEl.addEventListener('timeupdate', handleTimeUpdate);
        videoEl.addEventListener('seeked', handleTimeUpdate);

        return () => {
            videoEl?.removeEventListener('timeupdate', handleTimeUpdate);
            videoEl?.removeEventListener('seeked', handleTimeUpdate);
        };
    });

    function handleKeyDownEvent(event: KeyboardEvent) {
        // Only handle keyboard shortcuts when the player is hovered
        if (!isHovered) return;

        // Ignore when typing in inputs / textareas
        const target = event.target as HTMLElement;
        if (target?.tagName === 'INPUT' || target?.tagName === 'TEXTAREA') return;

        if (event.code === 'Space') {
            event.preventDefault(); // prevent page scroll

            if (!videoEl) return;

            if (videoEl.paused) {
                videoEl.play();
            } else {
                videoEl.pause();
            }
        }
    }

    function onseeked(event: Event) {
        const target = event.target as HTMLVideoElement;
        playbackTime = target.currentTime;
    }
</script>

<svelte:window onkeydown={handleKeyDownEvent} />

<div
    role="region"
    aria-label="Video player"
    class="relative h-full w-full"
    onmouseenter={() => {
        isHovered = true;
    }}
    onmouseleave={() => {
        isHovered = false;
    }}
>
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
