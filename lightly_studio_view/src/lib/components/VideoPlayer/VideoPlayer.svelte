<script lang="ts">
    import type { HTMLVideoAttributes } from 'svelte/elements';
    import { MEDIA_ERROR_MESSAGES } from './errors';

    interface VideoPlayerProps {
        src: string;
        videoEl?: HTMLVideoElement | null;
        videoProps?: HTMLVideoAttributes;
    }

    let { src, videoEl = $bindable(null), videoProps = {} }: VideoPlayerProps = $props();

    const defaultVideoProps: HTMLVideoAttributes = {
        muted: true,
        playsinline: true,
        controls: false,
        preload: 'metadata'
    };

    const mergedVideoProps = { ...defaultVideoProps, ...videoProps };

    let sourceLoadError = $state<string | null>(null);
    let isHovered = $state(false);

    function handleVideoError() {
        const errorCode = videoEl?.error?.code;
        sourceLoadError = errorCode
            ? MEDIA_ERROR_MESSAGES[errorCode]
            : 'Failed to load video source.';
    }

    function handleKeyDownEvent(event: KeyboardEvent) {
        // Only handle keyboard shortcuts when the player is hovered
        if (!isHovered) return;

        // Ignore when typing in inputs / textareas
        const target = event.target as HTMLElement;
        if (target?.tagName === 'INPUT' || target?.tagName === 'TEXTAREA') return;

        if (event.code === 'Space') {
            // Ignore repeat events when key is held down
            if (event.repeat) return;

            event.preventDefault(); // prevent page scroll

            if (!videoEl) return;

            if (videoEl.paused) {
                videoEl.play();
            } else {
                videoEl.pause();
            }
        }
    }
</script>

<svelte:window onkeydown={handleKeyDownEvent} />

<div
    role="region"
    aria-label="Video player"
    class="relative h-full w-full"
    onmouseenter={() => (isHovered = true)}
    onmouseleave={() => (isHovered = false)}
>
    <video
        bind:this={videoEl}
        {src}
        onerror={handleVideoError}
        onloadeddata={() => (sourceLoadError = null)}
        {...mergedVideoProps}
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
