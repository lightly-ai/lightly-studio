<script lang="ts">
    interface Props {
        /** Inclusive zero-based index of the first tick in the buffered range. */
        startIndex: number;
        /** Inclusive zero-based index of the last tick in the buffered range. */
        endIndex: number;
        /** Total number of ticks represented by the timeline. */
        tickCount: number;
    }

    let { startIndex, endIndex, tickCount }: Props = $props();

    const left = $derived(tickCount > 0 ? `${(startIndex / tickCount) * 100}%` : '0%');
    const width = $derived(
        tickCount > 0 ? `${((endIndex - startIndex + 1) / tickCount) * 100}%` : '0%'
    );
</script>

<div
    class="absolute inset-y-0 rounded bg-primary/30"
    style:left
    style:width
    data-testid="timeline-buffered-range"
></div>
