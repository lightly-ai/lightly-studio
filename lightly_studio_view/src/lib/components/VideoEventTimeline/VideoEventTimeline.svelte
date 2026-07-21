<script lang="ts">
    /**
     * Renders time-bounded video events as clickable bars positioned by their
     * start and end time.
     *
     * Overlapping events are stacked into separate lanes so none is hidden.
     * Clicking a bar seeks the associated player via {@link onSeek}, and an
     * optional playhead marks the current playback position.
     *
     * The component is presentation-only: pass in already-derived
     * {@link VideoEvent}s (see `toVideoEvents`) so it can be reused for any
     * temporal-annotation source.
     *
     * @example
     * ```svelte
     * <VideoEventTimeline
     *   events={toVideoEvents(video.sample.annotations)}
     *   durationS={video.duration_s ?? 0}
     *   currentTimeS={playbackTime}
     *   onSeek={(t) => (videoEl.currentTime = t)}
     * />
     * ```
     */
    import { cn } from '$lib/utils/shadcn.js';
    import { assignEventLanes, type VideoEvent } from '$lib/utils';

    interface VideoEventTimelineProps {
        /** Events to render, e.g. from `toVideoEvents`. */
        events: VideoEvent[];
        /** Total video duration in seconds; used to position bars. */
        durationS: number;
        /** Current playback time in seconds for the playhead indicator. */
        currentTimeS?: number;
        /** Called with the target time in seconds when a bar is clicked. */
        onSeek?: (timeS: number) => void;
        /** Heading shown above the timeline. */
        title?: string;
        /** Whether to render the title/count header above the track. */
        showHeader?: boolean;
        /** Extra classes for the outer container. */
        class?: string;
    }

    let {
        events,
        durationS,
        currentTimeS = 0,
        onSeek,
        title = 'Events',
        showHeader = true,
        class: className
    }: VideoEventTimelineProps = $props();

    const LANE_HEIGHT_PX = 22;
    const LANE_GAP_PX = 4;
    // Keep very short events clickable even when they occupy a sliver of the track.
    const MIN_BAR_WIDTH_PERCENT = 0.75;

    const lanes = $derived(assignEventLanes(events));
    const trackHeightPx = $derived(
        Math.max(1, lanes.laneCount) * LANE_HEIGHT_PX +
            Math.max(0, lanes.laneCount - 1) * LANE_GAP_PX
    );

    const clampPercent = (value: number) => Math.min(100, Math.max(0, value));

    const toPercent = (timeS: number) =>
        durationS > 0 ? clampPercent((timeS / durationS) * 100) : 0;

    function formatTime(timeS: number): string {
        const totalSeconds = Math.max(0, Math.round(timeS));
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }
</script>

<div class={cn('flex flex-col gap-2', className)} data-testid="video-event-timeline">
    {#if showHeader}
        <div class="flex items-center justify-between text-xs text-muted-foreground">
            <span class="font-medium">{title}</span>
            <span>{events.length}</span>
        </div>
    {/if}

    {#if events.length === 0}
        <p class="text-xs text-muted-foreground">No events for this video.</p>
    {:else}
        <div
            class="relative w-full rounded-md bg-muted/40"
            style={`height: ${trackHeightPx}px;`}
            role="group"
            aria-label={title}
        >
            {#each lanes.events as event (event.id)}
                {@const widthPercent = Math.max(
                    MIN_BAR_WIDTH_PERCENT,
                    toPercent(event.endTimeS) - toPercent(event.startTimeS)
                )}
                {@const leftPercent = Math.min(toPercent(event.startTimeS), 100 - widthPercent)}
                {@const timeRange = `${formatTime(event.startTimeS)}–${formatTime(event.endTimeS)}`}
                <div
                    class="absolute"
                    style={`left: ${leftPercent}%; width: ${widthPercent}%; top: ${
                        event.lane * (LANE_HEIGHT_PX + LANE_GAP_PX)
                    }px; height: ${LANE_HEIGHT_PX}px;`}
                >
                    <button
                        type="button"
                        class="flex h-full w-full items-center overflow-hidden rounded-sm border px-1.5 text-left text-[11px] leading-none transition-[filter] hover:brightness-110 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        style={`background-color: ${event.color}; border-color: ${event.contrastColor};`}
                        title={`${event.label} · ${timeRange}`}
                        aria-label={`Seek to ${event.label} at ${timeRange}`}
                        onclick={() => onSeek?.(event.startTimeS)}
                    >
                        <span class="truncate">{event.label}</span>
                    </button>
                </div>
            {/each}

            {#if durationS > 0}
                <div
                    class="pointer-events-none absolute top-0 z-10 h-full w-0.5 bg-primary"
                    style={`left: ${toPercent(currentTimeS)}%;`}
                    aria-hidden="true"
                ></div>
            {/if}
        </div>
    {/if}
</div>
