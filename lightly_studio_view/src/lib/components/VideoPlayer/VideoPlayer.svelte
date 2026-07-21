<script lang="ts">
    /**
     * A video player component with hover state and customizable styling.
     *
     * Features:
     * - Automatic hover detection with visual feedback
     * - Error handling with user-friendly messages
     * - Full control over video element attributes via videoProps
     * - Bindable video element reference for direct access
     * - Custom control bar whose full-width scrubber can host aligned timeline
     *   overlays that the native `<video controls>` bar cannot expose
     *
     * @example
     * ```svelte
     * <VideoPlayer
     *   src="video.mp4"
     *   hoverClass="ring-4 ring-green-500"
     * />
     * ```
     */
    import type { HTMLVideoAttributes } from 'svelte/elements';
    import { cn } from '$lib/utils/shadcn.js';
    import { MEDIA_ERROR_MESSAGES } from './errors';
    import VideoControls from '../VideoControls/VideoControls.svelte';
    import VideoEventTimeline from '../VideoEventTimeline/VideoEventTimeline.svelte';
    import { useVideoPlayback } from './useVideoPlayback.svelte';
    import type { VideoEvent } from '$lib/utils';

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

        /**
         * Start position in seconds for the current `src`; `null` waits (e.g.
         * until a frame deep-link timestamp is known).
         * @default 0
         */
        startTimeS?: number | null;

        /**
         * Time-bounded events rendered as a clickable bar aligned with the
         * scrubber. When empty, no event bar is shown.
         */
        events?: VideoEvent[];

        /**
         * Total video duration in seconds, used to position the event bars and
         * the scrubber. Falls back to the element's own duration once metadata
         * loads.
         */
        durationS?: number;

        /** Allow dragging event edges on the event bar to edit their time span. */
        editableEvents?: boolean;

        /** Called with the new span when an event edge finishes being edited. */
        onEventResize?: (event: VideoEvent, startTimeS: number, endTimeS: number) => void;
    }

    let {
        src,
        videoEl = $bindable(null),
        videoProps = {},
        hoverClass = 'outline outline-2 outline-blue-500',
        startTimeS = 0,
        events = [],
        durationS,
        editableEvents = false,
        onEventResize
    }: VideoPlayerProps = $props();

    const defaultVideoProps: HTMLVideoAttributes = {
        muted: true,
        playsinline: true,
        controls: false,
        preload: 'metadata'
    };

    // Derived so handlers from videoProps stay up to date. `class`, `onerror`, and
    // `onloadeddata` are applied separately: `class` to avoid overriding the merged
    // class; `onerror`/`onloadeddata` to chain consumer callbacks with the built-in
    // sourceLoadError logic rather than letting the spread silently overwrite them.
    const mergedVideoProps = $derived.by(() => {
        const restVideoProps = { ...videoProps };
        delete restVideoProps.class;
        delete restVideoProps.onerror;
        delete restVideoProps.onloadeddata;
        return {
            ...defaultVideoProps,
            ...restVideoProps,
            // Force native controls off — the custom bar replaces them.
            controls: false
        };
    });
    const videoClass = $derived(videoProps.class);

    let sourceLoadError = $state<string | null>(null);
    let isHovered = $state(false);
    let regionEl: HTMLDivElement | null = $state(null);

    // Mirror playback state and expose intent callbacks for the control bar.
    const playback = useVideoPlayback({
        getVideoEl: () => videoEl,
        getRegionEl: () => regionEl,
        getSrc: () => src,
        getStartTimeS: () => startTimeS,
        initialMuted: defaultVideoProps.muted ?? true
    });

    // Prefer an explicit duration (known before metadata loads) for the scrubber
    // and the event bar, so both share the same coordinate system.
    const effectiveDurationS = $derived(durationS ?? playback.durationS);
    const showEvents = $derived(events.length > 0);

    function handleVideoError() {
        const errorCode = videoEl?.error?.code;
        sourceLoadError = errorCode
            ? MEDIA_ERROR_MESSAGES[errorCode]
            : 'Failed to load video source.';
    }

    function handleMouseMove(event: MouseEvent) {
        if (!videoEl) return;

        const rect = videoEl.getBoundingClientRect();
        const isWithinBounds =
            event.clientX >= rect.left &&
            event.clientX <= rect.right &&
            event.clientY >= rect.top &&
            event.clientY <= rect.bottom;

        if (isWithinBounds && !isHovered) {
            isHovered = true;
            videoEl.focus();
        } else if (!isWithinBounds && isHovered) {
            isHovered = false;
            videoEl.blur();
        }
    }
</script>

<svelte:window onmousemove={handleMouseMove} />

<div
    bind:this={regionEl}
    role="region"
    aria-label="Video player"
    class="flex h-full min-h-0 w-full flex-col overflow-hidden bg-black"
>
    <!-- Absolute video so its intrinsic size can't force page scroll. -->
    <div class="relative min-h-0 w-full flex-1 overflow-hidden">
        <video
            bind:this={videoEl}
            class={cn(
                'absolute inset-0 h-full w-full cursor-pointer',
                videoClass,
                isHovered && hoverClass
            )}
            {src}
            {...mergedVideoProps}
            onerror={(e) => {
                handleVideoError();
                videoProps.onerror?.(e);
            }}
            onloadeddata={(e) => {
                sourceLoadError = null;
                videoProps.onloadeddata?.(e);
            }}
            onclick={playback.togglePlay}
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
    <VideoControls
        class="shrink-0"
        currentTimeS={playback.currentTimeS}
        durationS={effectiveDurationS}
        isPlaying={playback.isPlaying}
        isMuted={playback.isMuted}
        isFullscreen={playback.isFullscreen}
        onPlayPause={playback.togglePlay}
        onSeek={playback.seekTo}
        onToggleMute={playback.toggleMute}
        onToggleFullscreen={playback.toggleFullscreen}
    >
        {#if showEvents}
            <VideoEventTimeline
                class="w-full"
                {events}
                durationS={effectiveDurationS}
                currentTimeS={playback.currentTimeS}
                onSeek={playback.seekTo}
                editable={editableEvents}
                onResize={onEventResize}
                showHeader={false}
            />
        {/if}
    </VideoControls>
</div>
