<script lang="ts">
    import type { TickView } from '$lib/api/lightly_studio_local/types.gen';
    import { TimelineLane, getTimelineViewport } from '../TimelineViewport';

    interface BufferRange {
        /** Inclusive zero-based index of the first buffered tick. */
        startIndex: number;
        /** Inclusive zero-based index of the last buffered tick. */
        endIndex: number;
    }

    /** Ruler of sequence ticks with a slider to select the active tick. */
    interface Props {
        /** Sequence ticks (seq number + anchor timestamp). */
        ticks: TickView[];
        /** Seq number of the active tick; highlighted on the ruler. */
        currentTick: number;
        /** Inclusive tick-index ranges whose data is ready for playback. */
        bufferedRanges: readonly BufferRange[];
        /** Select a tick from the overlaid ruler slider. */
        onSelectTick: (seqNumber: number) => void;
        /** Preview the slider's current tick while the user is seeking. */
        onPreviewTick?: (seqNumber: number | null) => void;
        /** Called when the user starts dragging the slider. */
        onSeekStart?: () => void;
        /** Called when the user releases the slider. */
        onSeekEnd?: () => void;
    }

    let {
        ticks,
        currentTick,
        bufferedRanges,
        onSelectTick,
        onPreviewTick,
        onSeekStart,
        onSeekEnd
    }: Props = $props();

    const SEEK_KEYS = new Set([
        'ArrowLeft',
        'ArrowRight',
        'ArrowUp',
        'ArrowDown',
        'PageUp',
        'PageDown',
        'Home',
        'End'
    ]);
    let seekActive = false;
    let lastCommittedIndex: number | null = null;

    const beginSeek = () => {
        if (seekActive) return;
        seekActive = true;
        lastCommittedIndex = null;
        onSeekStart?.();
    };

    const commitSelectedTick = (input: HTMLInputElement) => {
        const index = Number(input.value);
        if (index === lastCommittedIndex) return;

        const tick = ticks[index];
        if (tick) {
            lastCommittedIndex = index;
            onSelectTick(tick.seq_number);
        }
    };

    const previewSelectedTick = (input: HTMLInputElement) => {
        onPreviewTick?.(ticks[Number(input.value)]?.seq_number ?? null);
    };

    const endSeek = () => {
        if (!seekActive) return;
        seekActive = false;
        lastCommittedIndex = null;
        onPreviewTick?.(null);
        onSeekEnd?.();
    };

    const NANOS_PER_SECOND = 1_000_000_000;

    /** Anchor the ruler at the first tick that carries a timestamp so labels stay relative. */
    const baseTimestampNs = $derived(
        ticks.find((tick) => tick.timestamp_ns !== null)?.timestamp_ns ?? null
    );

    /** Upper bound of rendered marks; longer sequences are thinned so marks stay visible. */
    const MAX_VISIBLE_MARKS = 200;
    /** Upper bound of labels across the visible window. */
    const MAX_VISIBLE_LABELS = 12;
    const TICK_GRID_GRADIENT =
        'linear-gradient(to right, transparent calc(100% - 1px), hsl(var(--border)) 0)';

    /** Smallest step of the form 1, 2 or 5 times a power of ten that is at least `minimum`. */
    const niceStep = (minimum: number): number => {
        for (let power = 1; ; power *= 10) {
            for (const factor of [1, 2, 5]) {
                if (factor * power >= minimum) return factor * power;
            }
        }
    };

    const viewport = getTimelineViewport();
    /** Zooming in shows fewer ticks at once, so marks thin out less. */
    const markStride = $derived(niceStep(ticks.length / (MAX_VISIBLE_MARKS * viewport.zoom)));
    // A multiple of the mark stride, so each label sits on a mark.
    const labelStride = $derived(
        markStride * niceStep(ticks.length / (MAX_VISIBLE_LABELS * viewport.zoom * markStride))
    );

    // Render only the marks inside the window, plus one window on each side, so zooming in does
    // not keep every offscreen mark in the DOM. Marks sit on round one-based frame numbers, so
    // they do not shift while panning and the labels read 10, 20, 30 and so on.
    const visibleMarks = $derived.by(() => {
        const span = ticks.length / viewport.zoom;
        const windowStart = viewport.offset * ticks.length;
        const first = Math.max(0, Math.floor(windowStart - span));
        const last = Math.min(ticks.length - 1, Math.ceil(windowStart + 2 * span));
        const marks = [];
        const firstFrame = Math.max(markStride, Math.ceil((first + 1) / markStride) * markStride);
        for (let index = firstFrame - 1; index <= last; index += markStride) {
            marks.push({ tick: ticks[index], index, isLabeled: (index + 1) % labelStride === 0 });
        }
        return marks;
    });

    const isBuffered = (index: number): boolean =>
        bufferedRanges.some((range) => index >= range.startIndex && index <= range.endIndex);

    const formatTickTime = (timestampNs: number | null): string | undefined => {
        if (timestampNs === null || baseTimestampNs === null) return undefined;
        return `${((timestampNs - baseTimestampNs) / NANOS_PER_SECOND).toFixed(2)}s`;
    };
</script>

<!-- Sticky to the top, so the ruler stays visible while the tracks scroll. Keep it `h-8`. -->
<div
    class="sticky top-0 z-20 flex h-8 w-full flex-none select-none flex-col overflow-hidden bg-background px-2 py-0.5"
>
    <div class="overflow-hidden px-1">
        <TimelineLane class="relative h-7 shrink-0">
            {#if ticks.length > 0 && ticks.length / viewport.zoom <= 100}
                <span
                    class="pointer-events-none absolute inset-0"
                    style:background-image={TICK_GRID_GRADIENT}
                    style:background-size={`${100 / ticks.length}% 100%`}
                    aria-hidden="true"
                ></span>
            {/if}
            {#each visibleMarks.filter((mark) => mark.isLabeled) as mark (mark.tick.seq_number)}
                <span
                    class="absolute top-1 -translate-x-1/2 text-[10px] leading-none text-muted-foreground"
                    style:left={`${((mark.index + 0.5) / ticks.length) * 100}%`}
                    >{mark.index + 1}</span
                >
            {/each}
            {#each visibleMarks as mark (mark.tick.seq_number)}
                <span
                    class="absolute bottom-0 z-10 w-px -translate-x-1/2 {isBuffered(mark.index)
                        ? 'bg-primary'
                        : 'bg-border'} {mark.isLabeled ? 'h-2' : 'h-1'}"
                    style:left={`${((mark.index + 0.5) / ticks.length) * 100}%`}
                    title={formatTickTime(mark.tick.timestamp_ns)}
                    data-testid="timeline-tick-mark"
                    data-labeled={mark.isLabeled || undefined}
                ></span>
            {/each}
            <input
                aria-label="Frame position"
                class="absolute bottom-0 z-20 h-3.5 cursor-pointer appearance-none bg-transparent accent-primary [&::-moz-range-thumb]:size-3.5 [&::-moz-range-thumb]:appearance-none [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:bg-primary [&::-moz-range-track]:bg-transparent [&::-webkit-slider-runnable-track]:bg-transparent [&::-webkit-slider-thumb]:size-3.5 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-primary"
                style:left={`calc(${ticks.length > 0 ? 50 / ticks.length : 0}% - 7px)`}
                style:width={`calc(100% - ${ticks.length > 0 ? 100 / ticks.length : 0}% + 14px)`}
                type="range"
                min="0"
                max={Math.max(0, ticks.length - 1)}
                value={Math.max(
                    0,
                    ticks.findIndex((tick) => tick.seq_number === currentTick)
                )}
                disabled={ticks.length === 0}
                onpointerdown={beginSeek}
                onpointerup={(event) => {
                    commitSelectedTick(event.currentTarget);
                    endSeek();
                }}
                onpointercancel={endSeek}
                oninput={(event) => previewSelectedTick(event.currentTarget)}
                onkeydown={(event) => {
                    if (SEEK_KEYS.has(event.key)) beginSeek();
                }}
                onkeyup={(event) => {
                    if (SEEK_KEYS.has(event.key)) {
                        commitSelectedTick(event.currentTarget);
                        endSeek();
                    }
                }}
                onblur={endSeek}
                onchange={(event) => commitSelectedTick(event.currentTarget)}
            />
        </TimelineLane>
    </div>
</div>
