<script lang="ts">
    import type { TickView } from '$lib/api/lightly_studio_local/types.gen';

    /** Ruler of sequence ticks plus one lane per channel. */
    interface Props {
        /** Sequence ticks (seq number + anchor timestamp). */
        ticks: TickView[];
        /** Seq numbers whose point-cloud data is already cached. */
        cachedTicks: number[];
        /** Seq number of the active tick; highlighted on the ruler. */
        currentTick: number;
        /** Lane names rendered beneath the ruler, in display order. */
        lanes: string[];
        /** Select a tick from the overlaid ruler slider. */
        onSelectTick: (seqNumber: number) => void;
    }

    let { ticks, cachedTicks, currentTick, lanes, onSelectTick }: Props = $props();

    const NANOS_PER_SECOND = 1_000_000_000;

    /** Anchor the ruler at the first tick that carries a timestamp so labels stay relative. */
    const baseTimestampNs = $derived(
        ticks.find((tick) => tick.timestamp_ns !== null)?.timestamp_ns ?? null
    );

    const formatTickTime = (timestampNs: number | null): string | undefined => {
        if (timestampNs === null || baseTimestampNs === null) return undefined;
        return `${((timestampNs - baseTimestampNs) / NANOS_PER_SECOND).toFixed(2)}s`;
    };
</script>

<div class="flex min-h-0 flex-1 flex-col gap-1 overflow-auto px-2 py-1.5">
    <div class="relative flex h-4 shrink-0 items-end gap-px">
        {#each ticks as tick (tick.seq_number)}
            <span
                class="w-full {tick.seq_number % 5 === 0 ? 'h-3' : 'h-1.5'} {cachedTicks.includes(
                    tick.seq_number
                )
                    ? 'bg-emerald-500'
                    : 'bg-border'}"
                title={`${formatTickTime(tick.timestamp_ns) ?? `Frame ${tick.seq_number + 1}`}${cachedTicks.includes(tick.seq_number) ? ' · cached' : ''}`}
            ></span>
        {/each}
        <input
            aria-label="Frame position"
            class="absolute top-0 h-4 cursor-pointer appearance-none bg-transparent accent-primary [&::-moz-range-track]:bg-transparent [&::-webkit-slider-runnable-track]:bg-transparent"
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
