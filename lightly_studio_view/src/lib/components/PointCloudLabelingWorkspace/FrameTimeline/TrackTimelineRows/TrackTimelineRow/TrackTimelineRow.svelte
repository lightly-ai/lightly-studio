<script lang="ts">
    import type { SequenceTrackView, TickView } from '$lib/api/lightly_studio_local/types.gen';
    import { getColorByLabel } from '$lib/utils';
    import { buildTrackRuns } from '../buildTrackRuns';
    import { getTrackExtent } from '../trackExtension';
    import TrackExtendHandles from './TrackExtendHandles.svelte';
    import { useTrackExtendDrag } from './useTrackExtendDrag.svelte';

    /** One track: its label and the ticks where the scene shows its annotations. */
    interface Props {
        ticks: TickView[];
        track: SequenceTrackView;
        isSelected: boolean;
        onSelectPosition: (event: MouseEvent, track: SequenceTrackView) => void;
        /** Set while editing: shows handles to resize the track's covered tick range. */
        onExtend?: (track: SequenceTrackView, startSeqNumber: number, endSeqNumber: number) => void;
        onExtendStart?: () => void;
        onExtendEnd?: () => void;
        /** Set while editing: asks to delete the track. */
        onRequestDelete?: (track: SequenceTrackView) => void;
    }

    let {
        ticks,
        track,
        isSelected,
        onSelectPosition,
        onExtend,
        onExtendStart = () => {},
        onExtendEnd = () => {},
        onRequestDelete
    }: Props = $props();
    let bar = $state<HTMLElement | null>(null);

    const runs = $derived(buildTrackRuns(ticks, track.annotations));
    const runTitle = (run: (typeof runs)[number]) => {
        const frames =
            run.startIndex === run.endIndex
                ? `Frame ${run.startIndex + 1}`
                : `Frames ${run.startIndex + 1}–${run.endIndex + 1}`;
        return `${frames} · ${run.interpolated ? 'interpolated' : 'drawn'}`;
    };
    const extent = $derived(getTrackExtent(runs));
    const drag = useTrackExtendDrag({
        getTicks: () => ticks,
        getExtent: () => extent,
        getBar: () => bar,
        onStart: () => onExtendStart(),
        onEnd: () => onExtendEnd(),
        onCommit: ({ start, end }) => onExtend?.(track, start, end)
    });
    const label = $derived(
        `${track.annotation_label_name} · Track ${track.object_track_number} · ${track.annotation_source_name}`
    );
</script>

<div class="py-1" data-track-id={track.object_track_id}>
    <div class="flex items-center justify-between gap-2 pb-0.5">
        <div
            class="truncate text-[10px] {isSelected
                ? 'font-semibold text-primary'
                : 'text-muted-foreground'}"
            title={label}
        >
            {label}
        </div>
        {#if onRequestDelete}
            <button
                type="button"
                class="shrink-0 rounded-sm px-1 text-xs leading-none text-muted-foreground hover:bg-destructive/20 hover:text-destructive"
                aria-label={`Delete ${track.annotation_label_name} track ${track.object_track_number}`}
                title="Delete track"
                onclick={() => onRequestDelete(track)}
            >
                ×
            </button>
        {/if}
    </div>
    <div class="relative" bind:this={bar}>
        <button
            type="button"
            class="relative block h-4 w-full cursor-pointer overflow-hidden rounded-sm bg-muted/40"
            aria-label={`Select ${track.annotation_label_name} track ${track.object_track_number} position`}
            onclick={(event) => onSelectPosition(event, track)}
        >
            {#each runs as run (run.startIndex)}
                <span
                    class="absolute inset-y-0"
                    style:left={`${(run.startIndex / ticks.length) * 100}%`}
                    style:width={`${((run.endIndex - run.startIndex + 1) / ticks.length) * 100}%`}
                    style:background-color={getColorByLabel(
                        track.annotation_label_name,
                        (run.interpolated ? 0.3 : 0.75) + (isSelected ? 0.2 : 0)
                    ).color}
                    title={runTitle(run)}
                ></span>
            {/each}
        </button>
        {#if extent}
            <TrackExtendHandles
                {extent}
                tickCount={ticks.length}
                {drag}
                label={`${track.annotation_label_name} track ${track.object_track_number}`}
                enabled={Boolean(onExtend)}
            />
        {/if}
    </div>
</div>
