<script lang="ts">
    import type { TickView } from '$lib/api/lightly_studio_local/types.gen';

    /** Ruler of sequence ticks plus one lane per channel. Placeholder lanes until frames land. */
    interface Props {
        /** Sequence ticks (seq number + anchor timestamp). */
        ticks: TickView[];
        /** Seq number of the active tick; highlighted on the ruler. */
        currentTick: number;
        /** Lane names rendered beneath the ruler, in display order. */
        lanes: string[];
    }

    let { ticks, currentTick, lanes }: Props = $props();

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
    <div class="flex h-4 shrink-0 items-end gap-px">
        {#each ticks as tick (tick.seq_number)}
            <span
                class="w-full {tick.seq_number === currentTick
                    ? 'h-4 bg-primary'
                    : tick.seq_number % 5 === 0
                      ? 'h-3 bg-border'
                      : 'h-1.5 bg-border'}"
                title={formatTickTime(tick.timestamp_ns)}
            ></span>
        {/each}
    </div>
    {#each lanes as lane (lane)}
        <div class="flex items-center gap-2">
            <span class="w-24 shrink-0 truncate text-xs text-muted-foreground">{lane}</span>
            <div class="h-4 flex-1 rounded bg-muted/50"></div>
        </div>
    {/each}
</div>
