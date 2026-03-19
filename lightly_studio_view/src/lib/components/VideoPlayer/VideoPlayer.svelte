<script lang="ts">
    /**
     * A video player component with hover state and customizable styling.
     *
     * Features:
     * - Automatic hover detection with visual feedback
     * - Error handling with user-friendly messages
     * - Full control over video element attributes via videoProps
     * - Bindable video element reference for direct access
     *
     * @example
     * ```svelte
     * <VideoPlayer
     *   src="video.mp4"
     *   videoProps={{ controls: true }}
     *   hoverClass="ring-4 ring-green-500"
     * />
     * ```
     */
    import type { HTMLVideoAttributes } from 'svelte/elements';
    import { cn } from '$lib/utils/shadcn.js';
    import { MEDIA_ERROR_MESSAGES } from './errors';

    interface VideoPlayerProps {
        /**
         * Video source URL (required)
         */
        src: string;

        /**
         * Bindable reference to the video element
         * @bindable
         */
        videoEl?: HTMLVideoElement | null;

        /**
         * Additional HTML video element attributes
         * Default: { muted: true, playsinline: true, controls: false, preload: 'metadata' }
         */
        videoProps?: HTMLVideoAttributes;

        /**
         * CSS classes to apply when video is hovered
         * @default 'outline outline-2 outline-blue-500'
         */
        hoverClass?: string;
    }

    let {
        src,
        videoEl = $bindable(null),
        videoProps = {},
        hoverClass = 'outline outline-2 outline-blue-500'
    }: VideoPlayerProps = $props();

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
        videoEl?.focus();
    };
    const onmouseleave = () => {
        isHovered = false;
        videoEl?.blur();
    };
</script>

<div role="region" aria-label="Video player" class="relative h-full w-full">
    <video
        {onmouseenter}
        {onmouseleave}
        bind:this={videoEl}
        class={cn(videoClass, isHovered && hoverClass)}
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
