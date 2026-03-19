<script lang="ts">
    import type { HTMLVideoAttributes } from 'svelte/elements';
    import { cn } from '$lib/utils/shadcn.js';
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

    const { class: videoClass, ...restVideoProps } = videoProps;
    const mergedVideoProps = { ...defaultVideoProps, ...restVideoProps };

    let sourceLoadError = $state<string | null>(null);
    let isHovered = $state(false);

    function handleVideoError() {
        const errorCode = videoEl?.error?.code;
        sourceLoadError = errorCode
            ? MEDIA_ERROR_MESSAGES[errorCode]
            : 'Failed to load video source.';
    }

    const onmouseenter = () => {
        isHovered = true;
    };
    const onmouseleave = () => {
        isHovered = false;
    };
</script>

<div
    role="region"
    aria-label="Video player"
    class="relative h-full w-full"
    {onmouseenter}
    {onmouseleave}
>
    <video
        bind:this={videoEl}
        class={cn(videoClass, isHovered && 'outline outline-2 outline-blue-500')}
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
