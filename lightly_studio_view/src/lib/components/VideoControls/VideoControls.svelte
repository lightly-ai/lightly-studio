<script lang="ts">
    /**
     * Presentation-only video controls: a full-width scrubber and transport
     * buttons. Full width so timeline overlays can share its coordinate system.
     * Owns no playback state; calls back on user intent (see {@link VideoPlayer}).
     */
    import type { Snippet } from 'svelte';
    import { Play, Pause, Volume2, VolumeX, Maximize, Minimize } from '@lucide/svelte';
    import { cn } from '$lib/utils/shadcn.js';
    import { formatTime, clampPercent, timeFromClientX } from './VideoControls.helpers';

    interface VideoControlsProps {
        currentTimeS: number;
        durationS: number;
        isPlaying: boolean;
        isMuted: boolean;
        isFullscreen: boolean;
        onPlayPause: () => void;
        onSeek: (timeS: number) => void;
        onToggleMute: () => void;
        onToggleFullscreen: () => void;
        /**
         * Optional content (e.g. an event bar) rendered below the transport
         * buttons. It sits in the same padded, full-width column as the scrubber,
         * so overlays share the scrubber's coordinate system and line up exactly.
         */
        children?: Snippet;
        class?: string;
    }

    let {
        currentTimeS,
        durationS,
        isPlaying,
        isMuted,
        isFullscreen,
        onPlayPause,
        onSeek,
        onToggleMute,
        onToggleFullscreen,
        children,
        class: className
    }: VideoControlsProps = $props();

    const SEEK_STEP_S = 5;
    // Bespoke over the Shadcn <Button>: these overlay the video, so they need
    // transparent backgrounds, white text, and a compact hit area rather than
    // the design system's surface-oriented button styling.
    const buttonClass =
        'flex items-center rounded p-0.5 hover:text-white/80 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring';

    let trackEl: HTMLDivElement | null = $state(null);
    let isDragging = false;

    const playedPercent = $derived(
        durationS > 0 ? clampPercent((currentTimeS / durationS) * 100) : 0
    );

    function seekToPointer(event: PointerEvent) {
        if (!trackEl) return;
        onSeek(timeFromClientX(event.clientX, trackEl.getBoundingClientRect(), durationS));
    }

    function stopDragging(pointerId?: number) {
        if (!isDragging) return;
        isDragging = false;
        if (pointerId !== undefined && trackEl?.hasPointerCapture(pointerId)) {
            trackEl.releasePointerCapture(pointerId);
        }
    }

    function handlePointerDown(event: PointerEvent) {
        if (durationS <= 0 || !trackEl) return;
        isDragging = true;
        trackEl.setPointerCapture(event.pointerId);
        seekToPointer(event);
    }

    function handlePointerMove(event: PointerEvent) {
        if (isDragging) seekToPointer(event);
    }

    function handleKeyDown(event: KeyboardEvent) {
        if (durationS <= 0) return;
        // Cap the step for short clips so one press never leaps the whole video.
        const stepS = Math.min(SEEK_STEP_S, durationS / 4);
        if (event.key === 'ArrowRight') {
            onSeek(Math.min(durationS, currentTimeS + stepS));
            event.preventDefault();
        } else if (event.key === 'ArrowLeft') {
            onSeek(Math.max(0, currentTimeS - stepS));
            event.preventDefault();
        }
    }
</script>

<div class={cn('flex w-full flex-col gap-1.5 px-3 pb-2 pt-1.5', className)}>
    <!-- Scrubber: full width so timeline overlays can share its coordinate space. -->
    <div
        bind:this={trackEl}
        class="group relative h-3 w-full cursor-pointer touch-none"
        role="slider"
        tabindex="0"
        aria-label="Seek"
        aria-valuemin={0}
        aria-valuemax={durationS}
        aria-valuenow={currentTimeS}
        aria-valuetext={`${formatTime(currentTimeS)} of ${formatTime(durationS)}`}
        onpointerdown={handlePointerDown}
        onpointermove={handlePointerMove}
        onpointerup={(event) => stopDragging(event.pointerId)}
        onpointercancel={(event) => stopDragging(event.pointerId)}
        onlostpointercapture={() => stopDragging()}
        onkeydown={handleKeyDown}
    >
        <div class="absolute top-1/2 h-1 w-full -translate-y-1/2 rounded-full bg-white/25"></div>
        <div
            class="absolute top-1/2 h-1 -translate-y-1/2 rounded-full bg-primary"
            style={`width: ${playedPercent}%;`}
        ></div>
        <div
            class="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary opacity-0 transition-opacity group-hover:opacity-100"
            style={`left: ${playedPercent}%;`}
        ></div>
    </div>

    <div class="flex items-center gap-3 text-xs text-white">
        <button
            type="button"
            class={buttonClass}
            aria-label={isPlaying ? 'Pause' : 'Play'}
            onclick={onPlayPause}
        >
            {#if isPlaying}
                <Pause class="size-4" />
            {:else}
                <Play class="size-4" />
            {/if}
        </button>

        <span class="tabular-nums text-white/90">
            {formatTime(currentTimeS)} / {formatTime(durationS)}
        </span>

        <div class="flex-1"></div>

        <button
            type="button"
            class={buttonClass}
            aria-label={isMuted ? 'Unmute' : 'Mute'}
            onclick={onToggleMute}
        >
            {#if isMuted}
                <VolumeX class="size-4" />
            {:else}
                <Volume2 class="size-4" />
            {/if}
        </button>

        <button
            type="button"
            class={buttonClass}
            aria-label={isFullscreen ? 'Exit full screen' : 'Full screen'}
            onclick={onToggleFullscreen}
        >
            {#if isFullscreen}
                <Minimize class="size-4" />
            {:else}
                <Maximize class="size-4" />
            {/if}
        </button>
    </div>
    {@render children?.()}
</div>
