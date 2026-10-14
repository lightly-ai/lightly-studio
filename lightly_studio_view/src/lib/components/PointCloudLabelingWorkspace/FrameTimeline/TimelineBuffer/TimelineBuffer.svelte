<script lang="ts">
    import TimelineBufferedRange from './TimelineBufferedRange/TimelineBufferedRange.svelte';

    interface BufferRange {
        /** Inclusive zero-based index of the first buffered tick. */
        startIndex: number;
        /** Inclusive zero-based index of the last buffered tick. */
        endIndex: number;
    }

    interface Props {
        /** Number of ticks represented by the timeline. */
        tickCount: number;
        /** Buffered inclusive index ranges, in timeline display order. */
        bufferedRanges: readonly BufferRange[];
    }

    let { tickCount, bufferedRanges }: Props = $props();
</script>

<div class="pointer-events-none absolute inset-x-0 bottom-0 h-1" aria-hidden="true">
    {#each bufferedRanges as range}
        <TimelineBufferedRange
            {tickCount}
            startIndex={range.startIndex}
            endIndex={range.endIndex}
        />
    {/each}
</div>
