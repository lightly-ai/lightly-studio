<script lang="ts">
    import type { SequenceTrackView, TickView } from '$lib/api/lightly_studio_local/types.gen';
    import TrackTimelineRow from './TrackTimelineRow/TrackTimelineRow.svelte';

    interface Props {
        ticks: TickView[];
        tracks: SequenceTrackView[];
        selectedAnnotationId: string | null;
        onSelectAnnotation: (annotationId: string) => void;
        onSelectTick: (seqNumber: number) => void;
    }

    let { ticks, tracks, selectedAnnotationId, onSelectAnnotation, onSelectTick }: Props = $props();
    const selectedTrackKey = $derived(
        tracks.find((track) =>
            track.annotations.some(
                (annotation) => annotation.annotation_id === selectedAnnotationId
            )
        )
    );

    const selectTrackPosition = (event: MouseEvent, track: SequenceTrackView) => {
        if (ticks.length === 0) return;

        const bounds = (event.currentTarget as HTMLButtonElement).getBoundingClientRect();
        if (bounds.width === 0) return;
        const position = (event.clientX - bounds.left) / bounds.width;
        const index = Math.min(ticks.length - 1, Math.floor(position * ticks.length));
        const tick = ticks[index];
        if (!tick) return;

        onSelectTick(tick.seq_number);
        const annotation = track.annotations.find((item) => item.seq_number === tick.seq_number);
        if (annotation) onSelectAnnotation(annotation.annotation_id);
    };
</script>

{#if tracks.length > 0}
    <div class="border-t px-2 py-1" data-testid="object-track-rows">
        {#each tracks as track (`${track.object_track_id}-${track.annotation_source_id}`)}
            <TrackTimelineRow
                {ticks}
                {track}
                isSelected={selectedTrackKey?.object_track_id === track.object_track_id &&
                    selectedTrackKey.annotation_source_id === track.annotation_source_id}
                onSelectPosition={selectTrackPosition}
            />
        {/each}
    </div>
{/if}
