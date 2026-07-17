<script lang="ts">
    /**
     * Renders time-bounded video events as clickable bars positioned by their
     * start and end time.
     *
     * Overlapping events are stacked into separate lanes so none is hidden.
     * Clicking a bar seeks the associated player via {@link onSeek}, and an
     * optional playhead marks the current playback position.
     *
     * When `editable` is set, each bar grows drag handles on its start/end edges
     * so the event's time span can be adjusted; committed edits are reported via
     * {@link onResize}. Edits are previewed optimistically until the parent feeds
     * back updated `events`.
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
        /** When true, event edges can be dragged to change their start/end time. */
        editable?: boolean;
        /** Called with the new span when an event edge finishes being edited. */
        onResize?: (event: VideoEvent, startTimeS: number, endTimeS: number) => void;
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
        editable = false,
        onResize,
        title = 'Events',
        showHeader = true,
        class: className
    }: VideoEventTimelineProps = $props();

    const LANE_HEIGHT_PX = 22;
    const LANE_GAP_PX = 4;
    // Keep very short events clickable even when they occupy a sliver of the track.
    const MIN_BAR_WIDTH_PERCENT = 0.75;
    // Smallest span an edit may collapse an event to.
    const MIN_EVENT_DURATION_S = 0.1;

    type Span = { startTimeS: number; endTimeS: number };
    type Edge = 'start' | 'end';

    const lanes = $derived(assignEventLanes(events));
    const trackHeightPx = $derived(
        Math.max(1, lanes.laneCount) * LANE_HEIGHT_PX +
            Math.max(0, lanes.laneCount - 1) * LANE_GAP_PX
    );

    let trackEl: HTMLDivElement | null = $state(null);
    // Optimistic overrides while an edit is in flight, keyed by event id.
    let pendingEdits = $state<Record<string, Span>>({});
    let dragging = $state<{ id: string; edge: Edge } | null>(null);

    // Drop optimistic overrides once the parent feeds back fresh events.
    $effect(() => {
        void events;
        pendingEdits = {};
    });

    const clampPercent = (value: number) => Math.min(100, Math.max(0, value));

    const toPercent = (timeS: number) =>
        durationS > 0 ? clampPercent((timeS / durationS) * 100) : 0;

    function effectiveSpan(event: VideoEvent): Span {
        return pendingEdits[event.id] ?? { startTimeS: event.startTimeS, endTimeS: event.endTimeS };
    }

    function clampSpan(span: Span, edge: Edge, timeS: number): Span {
        if (edge === 'start') {
            return {
                startTimeS: Math.max(0, Math.min(timeS, span.endTimeS - MIN_EVENT_DURATION_S)),
                endTimeS: span.endTimeS
            };
        }
        return {
            startTimeS: span.startTimeS,
            endTimeS: Math.min(durationS, Math.max(timeS, span.startTimeS + MIN_EVENT_DURATION_S))
        };
    }

    function timeFromClientX(clientX: number): number {
        if (!trackEl || durationS <= 0) return 0;
        const rect = trackEl.getBoundingClientRect();
        const ratio = rect.width > 0 ? (clientX - rect.left) / rect.width : 0;
        return Math.min(durationS, Math.max(0, ratio * durationS));
    }

    function formatTime(timeS: number): string {
        const totalSeconds = Math.max(0, Math.round(timeS));
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        return `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }

    const edgeTime = (span: Span, edge: Edge) =>
        edge === 'start' ? span.startTimeS : span.endTimeS;

    function startResize(pointerEvent: PointerEvent, event: VideoEvent, edge: Edge) {
        if (durationS <= 0) return;
        pointerEvent.stopPropagation();
        pointerEvent.preventDefault();
        dragging = { id: event.id, edge };
        (pointerEvent.currentTarget as HTMLElement).setPointerCapture(pointerEvent.pointerId);
        const seed = effectiveSpan(event);
        pendingEdits = { ...pendingEdits, [event.id]: seed };
        // Sync playback to the grabbed edge so the frame at that time is visible.
        onSeek?.(edgeTime(seed, edge));
    }

    function moveResize(pointerEvent: PointerEvent, event: VideoEvent) {
        if (!dragging || dragging.id !== event.id) return;
        const next = clampSpan(
            effectiveSpan(event),
            dragging.edge,
            timeFromClientX(pointerEvent.clientX)
        );
        pendingEdits = { ...pendingEdits, [event.id]: next };
        // Follow the dragged edge with the play position for live visual feedback.
        onSeek?.(edgeTime(next, dragging.edge));
    }

    function endResize(pointerEvent: PointerEvent, event: VideoEvent) {
        if (!dragging || dragging.id !== event.id) return;
        (pointerEvent.currentTarget as HTMLElement).releasePointerCapture(pointerEvent.pointerId);
        dragging = null;
        const span = pendingEdits[event.id];
        if (span) onResize?.(event, span.startTimeS, span.endTimeS);
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
            bind:this={trackEl}
            class="relative w-full rounded-md bg-muted/40"
            style={`height: ${trackHeightPx}px;`}
            role="group"
            aria-label={title}
        >
            {#each lanes.events as event (event.id)}
                {@const span = effectiveSpan(event)}
                {@const leftPercent = toPercent(span.startTimeS)}
                {@const widthPercent = Math.max(
                    MIN_BAR_WIDTH_PERCENT,
                    toPercent(span.endTimeS) - leftPercent
                )}
                {@const timeRange = `${formatTime(span.startTimeS)}–${formatTime(span.endTimeS)}`}
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
                        onclick={() => onSeek?.(span.startTimeS)}
                    >
                        <span class="truncate">{event.label}</span>
                    </button>

                    {#if editable}
                        {#each ['start', 'end'] as const as edge (edge)}
                            <div
                                class={cn(
                                    'absolute top-0 z-20 h-full w-2 cursor-ew-resize touch-none rounded-sm bg-white/70 hover:bg-white',
                                    edge === 'start' ? 'left-0' : 'right-0'
                                )}
                                role="slider"
                                tabindex="0"
                                aria-label={`Adjust ${event.label} ${edge} time`}
                                aria-valuemin={0}
                                aria-valuemax={durationS}
                                aria-valuenow={edge === 'start' ? span.startTimeS : span.endTimeS}
                                onpointerdown={(e) => startResize(e, event, edge)}
                                onpointermove={(e) => moveResize(e, event)}
                                onpointerup={(e) => endResize(e, event)}
                            ></div>
                        {/each}
                    {/if}
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
