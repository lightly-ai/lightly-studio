<script lang="ts">
    import type { TickView } from '$lib/api/lightly_studio_local/types.gen';

    /** Ruler of sequence ticks plus one lane per channel. Placeholder lanes until frames land. */
    interface Props {
        /** Sequence ticks (seq number + anchor timestamp). */
        ticks: TickView[];
        /** Seq number of the active tick; highlighted on the ruler. */
        currentTick: number;
        /** Tick numbers whose data has been buffered ahead of playback. */
        bufferedTickNumbers: readonly number[];
        /** Lane names rendered beneath the ruler, in display order. */
        lanes: string[];
        /** Select a tick from the overlaid ruler slider. */
        onSelectTick: (seqNumber: number) => void;
    }

    let { ticks, currentTick, bufferedTickNumbers, lanes, onSelectTick }: Props = $props();

    const NANOS_PER_SECOND = 1_000_000_000;

    /** Anchor the ruler at the first tick that carries a timestamp so labels stay relative. */
    const baseTimestampNs = $derived(
        ticks.find((tick) => tick.timestamp_ns !== null)?.timestamp_ns ?? null
    );
    const activeIndex = $derived(ticks.findIndex((tick) => tick.seq_number === currentTick));
    const bufferedRanges = $derived.by(() => {
        const buffered = new Set(bufferedTickNumbers);
        if (activeIndex >= 0) buffered.add(currentTick);

        const ranges: Array<{ left: string; width: string }> = [];
        let rangeStart: number | undefined;
        for (const [index, tick] of ticks.entries()) {
            const isBuffered = buffered.has(tick.seq_number);
            if (isBuffered && rangeStart === undefined) rangeStart = index;
            if ((!isBuffered || index === ticks.length - 1) && rangeStart !== undefined) {
                const rangeEnd = isBuffered && index === ticks.length - 1 ? index : index - 1;
                ranges.push({
                    left: `${(rangeStart / ticks.length) * 100}%`,
                    width: `${((rangeEnd - rangeStart + 1) / ticks.length) * 100}%`
                });
                rangeStart = undefined;
            }
        }
        return ranges;
    });

    const formatTickTime = (timestampNs: number | null): string | undefined => {
        if (timestampNs === null || baseTimestampNs === null) return undefined;
        return `${((timestampNs - baseTimestampNs) / NANOS_PER_SECOND).toFixed(2)}s`;
    };
</script>

<div class="scrollbar-thin flex min-h-0 flex-1 flex-col gap-1 overflow-auto px-2 py-1.5">
    <div class="relative flex h-4 shrink-0 items-end gap-px">
        {#each bufferedRanges as range}
            <div
                class="pointer-events-none absolute bottom-0 h-1 rounded bg-primary/30"
                style:left={range.left}
                style:width={range.width}
                aria-label="Buffered frames"
                data-testid="timeline-buffered-range"
            ></div>
        {/each}
        {#each ticks as tick (tick.seq_number)}
            <span
                class="w-full {tick.seq_number % 5 === 0 ? 'h-3 bg-border' : 'h-1.5 bg-border'}"
                title={formatTickTime(tick.timestamp_ns)}
            ></span>
        {/each}
        <input
            aria-label="Frame position"
            class="absolute top-0 h-4 cursor-pointer appearance-none bg-transparent accent-primary [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:w-6 [&::-moz-range-thumb]:rounded-md [&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:bg-primary [&::-moz-range-track]:bg-transparent [&::-webkit-slider-runnable-track]:bg-transparent [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-6 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-md [&::-webkit-slider-thumb]:bg-primary"
            style:left={ticks.length > 0 ? `${50 / ticks.length}%` : '0%'}
            style:right={ticks.length > 0 ? `${50 / ticks.length}%` : '0%'}
            style:width={`calc(100% - ${ticks.length > 0 ? 100 / ticks.length : 0}%)`}
            type="range"
            min="0"
            max={Math.max(0, ticks.length - 1)}
            value={Math.max(
                0,
                ticks.findIndex((tick) => tick.seq_number === currentTick)
            )}
            disabled={ticks.length === 0}
            oninput={(event) => {
                const tick = ticks[Number(event.currentTarget.value)];
                if (tick) onSelectTick(tick.seq_number);
            }}
        />
    </div>
    {#each lanes as lane (lane)}
        <div class="flex items-center gap-2">
            <span class="w-24 shrink-0 truncate text-xs text-muted-foreground">{lane}</span>
            <div class="h-4 flex-1 rounded bg-muted/50"></div>
        </div>
    {/each}
</div>
