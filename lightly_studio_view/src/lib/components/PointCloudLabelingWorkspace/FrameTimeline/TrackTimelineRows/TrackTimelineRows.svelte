<script lang="ts">
    import type { SequenceTrackView, TickView } from '$lib/api/lightly_studio_local/types.gen';
    import { Button } from '$lib/components/ui/button';
    import TrackTimelineRow from './TrackTimelineRow/TrackTimelineRow.svelte';

    interface Props {
        ticks: TickView[];
        tracks: SequenceTrackView[];
        selectedAnnotationId: string | null;
        onSelectAnnotation: (annotationId: string) => void;
        onSelectTick: (seqNumber: number) => void;
        /** Starts a track from the selected cuboid; set only while that is possible. */
        onStartTrack?: () => void;
        /** Arms or cancels adding a new track; set only while editing. */
        onAddTrack?: () => void;
        isAddingTrack?: boolean;
        /** Set while editing: extends a track onto the ticks from start to end (seq numbers). */
        onExtendTrack?: (
            track: SequenceTrackView,
            startSeqNumber: number,
            endSeqNumber: number
        ) => void;
        onExtendStart?: () => void;
        onExtendEnd?: () => void;
    }

    let {
        ticks,
        tracks,
        selectedAnnotationId,
        onSelectAnnotation,
        onSelectTick,
        onStartTrack,
        onAddTrack,
        isAddingTrack = false,
        onExtendTrack,
        onExtendStart,
        onExtendEnd
    }: Props = $props();
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

{#if tracks.length > 0 || onStartTrack || onAddTrack}
    <div class="border-t px-2 py-1" data-testid="object-track-rows">
        {#if onAddTrack || onStartTrack}
            <div class="mb-1 flex items-center gap-2">
                {#if onAddTrack}
                    <Button
                        variant={isAddingTrack ? 'default' : 'outline'}
                        size="sm"
                        class="h-6 text-xs"
                        onclick={onAddTrack}
                    >
                        {isAddingTrack ? 'Cancel' : 'Add object track'}
                    </Button>
                    {#if isAddingTrack}
                        <span class="text-xs text-muted-foreground">
                            Click in the 3D scene to place the first cuboid.
                        </span>
                    {/if}
                {/if}
                {#if onStartTrack}
                    <Button variant="outline" size="sm" class="h-6 text-xs" onclick={onStartTrack}>
                        Start track from selected cuboid
                    </Button>
                {/if}
            </div>
        {/if}
        {#each tracks as track (`${track.object_track_id}-${track.annotation_source_id}`)}
            <TrackTimelineRow
                {ticks}
                {track}
                isSelected={selectedTrackKey?.object_track_id === track.object_track_id &&
                    selectedTrackKey.annotation_source_id === track.annotation_source_id}
                onSelectPosition={selectTrackPosition}
                onExtend={onExtendTrack}
                {onExtendStart}
                {onExtendEnd}
            />
        {/each}
    </div>
{/if}
