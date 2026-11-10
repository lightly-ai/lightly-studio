<script lang="ts">
    import type { ExtendEdge } from '../trackExtension';
    import type { useTrackExtendDrag } from './useTrackExtendDrag.svelte';

    /** Drag handles for a track range, plus the preview of the proposed coverage. */
    interface Props {
        extent: { first: number; last: number };
        tickCount: number;
        drag: ReturnType<typeof useTrackExtendDrag>;
        label: string;
        enabled: boolean;
    }

    let { extent, tickCount, drag, label, enabled }: Props = $props();
    const percent = (index: number) => `${(index / tickCount) * 100}%`;
    const displayedExtent = $derived(drag.proposed ?? extent);
    const isPointExtent = $derived(extent.first === extent.last);
    const pointIndex = $derived.by(() => {
        if (drag.edge !== 'point' || !drag.proposed) return extent.first + 0.5;
        if (drag.proposed.first < extent.first) return drag.proposed.first;
        if (drag.proposed.last > extent.last) return drag.proposed.last + 1;
        return extent.first + 0.5;
    });
    const handles: { edge: ExtendEdge; index: number; isEnd: boolean }[] = $derived.by(() => {
        if (drag.edge === 'point') {
            return [{ edge: 'point', index: pointIndex, isEnd: pointIndex > extent.first + 0.5 }];
        }
        if (isPointExtent) return [{ edge: 'point', index: pointIndex, isEnd: false }];
        return [
            { edge: 'start', index: displayedExtent.first, isEnd: false },
            { edge: 'end', index: displayedExtent.last + 1, isEnd: true }
        ];
    });
    const activeHandle = $derived(handles.find(({ edge }) => edge === drag.edge));
    const proposedRange = $derived.by(() => {
        if (!drag.proposed) return null;
        const first = drag.proposed.first + 1;
        const last = drag.proposed.last + 1;
        return first === last ? `Tick ${first}` : `Ticks ${first}–${last}`;
    });
</script>

{#if drag.proposed}
    <span
        class="pointer-events-none absolute inset-y-0 rounded-sm border border-dashed border-primary bg-primary/30"
        style:left={percent(drag.proposed.first)}
        style:width={`${((drag.proposed.last - drag.proposed.first + 1) / tickCount) * 100}%`}
        data-testid="track-extend-preview"
    ></span>
{/if}
{#if activeHandle && proposedRange}
    <span
        role="tooltip"
        class="pointer-events-none absolute bottom-full z-20 mb-1 -translate-x-1/2 whitespace-nowrap rounded bg-popover px-2 py-1 text-[10px] text-popover-foreground shadow-md"
        style:left={percent(activeHandle.index)}
        data-testid="track-extend-tooltip"
    >
        {proposedRange}
    </span>
{/if}
{#if enabled}
    {#each handles as handle (handle.edge)}
        <div
            role="slider"
            tabindex="-1"
            aria-label={handle.edge === 'point'
                ? `Resize ${label}`
                : `Resize ${handle.edge} of ${label}`}
            aria-valuenow={handle.index}
            class="absolute right-0 top-0 z-10 ml-0.5 h-4 w-4 cursor-ew-resize touch-none rounded-full bg-foreground/80 hover:bg-primary {handle.edge ===
                'end'
                ? '-translate-x-full'
                : '-translate-x-1/2'}"
            style:left={percent(handle.index)}
            data-testid={`track-extend-${handle.edge}`}
            onpointerdown={(event) => drag.start(event, handle.edge)}
            onpointermove={drag.move}
            onpointerup={() => drag.finish(true)}
            onpointercancel={() => drag.finish(false)}
        ></div>
    {/each}
{/if}
