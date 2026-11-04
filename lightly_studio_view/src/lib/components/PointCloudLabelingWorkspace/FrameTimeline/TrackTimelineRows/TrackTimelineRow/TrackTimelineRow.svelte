<script lang="ts">
    import type { SequenceTrackView, TickView } from '$lib/api/lightly_studio_local/types.gen';
    import { getColorByLabel } from '$lib/utils';
    import { buildTrackRuns } from '../buildTrackRuns';

    /** One track: its label and the ticks where the scene shows its annotations. */
    interface Props {
        ticks: TickView[];
        track: SequenceTrackView;
        isSelected: boolean;
        onSelectPosition: (event: MouseEvent, track: SequenceTrackView) => void;
    }

    let { ticks, track, isSelected, onSelectPosition }: Props = $props();

    const runs = $derived(buildTrackRuns(ticks, track.annotations));
    const runTitle = (run: (typeof runs)[number]) => {
        const frames =
            run.startIndex === run.endIndex
                ? `Frame ${run.startIndex + 1}`
                : `Frames ${run.startIndex + 1}–${run.endIndex + 1}`;
        return `${frames} · ${run.interpolated ? 'generated' : 'drawn'}`;
    };
    const label = $derived(
        `${track.annotation_label_name} · Track ${track.object_track_number} · ${track.annotation_source_name}`
    );
</script>

<div class="py-1" data-track-id={track.object_track_id}>
    <div
        class="truncate pb-0.5 text-[10px] {isSelected
            ? 'font-semibold text-primary'
            : 'text-muted-foreground'}"
        title={label}
    >
        {label}
    </div>
    <button
        type="button"
        class="relative block h-2 w-full cursor-pointer overflow-hidden rounded-sm bg-muted/40"
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
</div>
