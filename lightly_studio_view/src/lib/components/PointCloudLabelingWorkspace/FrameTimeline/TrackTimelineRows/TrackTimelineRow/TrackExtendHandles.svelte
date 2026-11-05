<script lang="ts">
    import type { ExtendEdge } from '../trackExtension';
    import type { useTrackExtendDrag } from './useTrackExtendDrag.svelte';

    /** Drag handles at both ends of a track bar, plus the preview of the proposed coverage. */
    interface Props {
        extent: { first: number; last: number };
        tickCount: number;
        drag: ReturnType<typeof useTrackExtendDrag>;
        label: string;
        enabled: boolean;
    }

    let { extent, tickCount, drag, label, enabled }: Props = $props();
    const percent = (index: number) => `${(index / tickCount) * 100}%`;
    const handles: { edge: ExtendEdge; index: number }[] = $derived([
        { edge: 'start', index: extent.first },
        { edge: 'end', index: extent.last + 1 }
    ]);
</script>

{#if drag.proposed}
    <span
        class="pointer-events-none absolute inset-y-0 rounded-sm border border-dashed border-primary bg-primary/30"
        style:left={percent(drag.proposed.first)}
        style:width={`${((drag.proposed.last - drag.proposed.first + 1) / tickCount) * 100}%`}
        data-testid="track-extend-preview"
    ></span>
{/if}
{#if enabled}
    {#each handles as handle (handle.edge)}
        <div
            role="slider"
            tabindex="-1"
            aria-label={`Extend ${handle.edge} of ${label}`}
            aria-valuenow={handle.index}
            class="absolute -top-0.5 z-10 h-3 w-1.5 -translate-x-1/2 cursor-ew-resize touch-none rounded-sm bg-foreground/80 hover:bg-primary"
            style:left={percent(handle.index)}
            data-testid={`track-extend-${handle.edge}`}
            onpointerdown={(event) => drag.start(event, handle.edge)}
            onpointermove={drag.move}
            onpointerup={() => drag.finish(true)}
            onpointercancel={() => drag.finish(false)}
        ></div>
    {/each}
{/if}
