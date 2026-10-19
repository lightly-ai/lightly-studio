<script lang="ts">
    import type { TickView } from '$lib/api/lightly_studio_local/types.gen';

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
        /** Called when the user starts dragging the slider. */
        onSeekStart?: () => void;
        /** Called when the user releases the slider. */
        onSeekEnd?: () => void;
    }

    let { ticks, currentTick, bufferedRanges, onSelectTick, onSeekStart, onSeekEnd }: Props =
        $props();

    const NANOS_PER_SECOND = 1_000_000_000;

    /** Anchor the ruler at the first tick that carries a timestamp so labels stay relative. */
    const baseTimestampNs = $derived(
        ticks.find((tick) => tick.timestamp_ns !== null)?.timestamp_ns ?? null
    );

    /** Upper bound of rendered marks; longer sequences are thinned so marks stay visible. */
    const MAX_VISIBLE_MARKS = 200;

    const markStride = $derived(Math.max(1, Math.ceil(ticks.length / MAX_VISIBLE_MARKS)));

    const visibleMarks = $derived(
        ticks.flatMap((tick, index) => (index % markStride === 0 ? [{ tick, index }] : []))
    );

    const isBuffered = (index: number): boolean =>
        bufferedRanges.some((range) => index >= range.startIndex && index <= range.endIndex);

    const formatTickTime = (timestampNs: number | null): string | undefined => {
        if (timestampNs === null || baseTimestampNs === null) return undefined;
        return `${((timestampNs - baseTimestampNs) / NANOS_PER_SECOND).toFixed(2)}s`;
    };
</script>

<div class="flex flex-none select-none flex-col gap-1 overflow-hidden px-2 py-1">
    <div class="relative flex h-4 shrink-0 items-end gap-px">
        {#each visibleMarks as mark (mark.tick.seq_number)}
            <span
                class="absolute bottom-0 z-10 w-px -translate-x-1/2 {isBuffered(mark.index)
                    ? 'bg-primary'
                    : 'bg-border'} {mark.index % (markStride * 5) === 0 ? 'h-3' : 'h-1.5'}"
                style:left={`${((mark.index + 0.5) / ticks.length) * 100}%`}
                title={formatTickTime(mark.tick.timestamp_ns)}
                data-testid="timeline-tick-mark"
            ></span>
        {/each}
        <input
            aria-label="Frame position"
            class="absolute top-0 z-20 h-4 cursor-pointer appearance-none bg-transparent accent-primary [&::-moz-range-track]:bg-transparent [&::-webkit-slider-runnable-track]:bg-transparent"
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
            onpointerdown={() => {
                onSeekStart?.();
            }}
            onpointerup={() => {
                onSeekEnd?.();
            }}
            onchange={(event) => {
                const tick = ticks[Number(event.currentTarget.value)];
                if (tick) onSelectTick(tick.seq_number);
            }}
        />
    </div>
</div>
