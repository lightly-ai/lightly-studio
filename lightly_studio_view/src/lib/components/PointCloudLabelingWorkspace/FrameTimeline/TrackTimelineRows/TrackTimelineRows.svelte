<script lang="ts">
    import type { SequenceTrackView, TickView } from '$lib/api/lightly_studio_local/types.gen';
    import { DeleteTrackDialog } from './DeleteTrackDialog';
    import TrackTimelineRow from './TrackTimelineRow/TrackTimelineRow.svelte';
    import { TrackRowsResizer, useTrackRowsHeight } from './TrackRowsResizer';
    import { TrackTimelineToolbar } from './TrackTimelineToolbar';
    import { useVisibleTracks } from './useVisibleTracks.svelte';

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
        /** Set while editing: deletes a track and its cuboids once confirmed. */
        onDeleteTrack?: (track: SequenceTrackView) => Promise<unknown>;
        /** Identifies the sequence, so the chosen tracks are remembered per sequence. */
        sequenceId?: string;
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
        onExtendEnd,
        onDeleteTrack,
        sequenceId
    }: Props = $props();
    const rowsHeight = useTrackRowsHeight();
    let listElement = $state<HTMLElement | null>(null);
    const visible = useVisibleTracks({
        getTracks: () => tracks,
        getSelectedAnnotationId: () => selectedAnnotationId,
        getStorageKey: () =>
            sequenceId ? `lightlyStudio_trackTimelineVisibleTracks_${sequenceId}` : undefined
    });
    let trackToDelete = $state<SequenceTrackView | null>(null);
    let isDeleteDialogOpen = $state(false);
    const requestDelete = (track: SequenceTrackView) => {
        trackToDelete = track;
        isDeleteDialogOpen = true;
    };
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
    {#if tracks.length > 0}
        <TrackRowsResizer {rowsHeight} getRenderedHeight={() => listElement?.clientHeight ?? 0} />
    {/if}
    <div class="border-t px-2 py-1" data-testid="object-track-rows">
        <TrackTimelineToolbar
            visibility={tracks.length > 0
                ? {
                      tracks,
                      visibleCount: visible.visibleTracks.length,
                      selectedKeys: visible.selectedKeys,
                      onChange: visible.setSelection
                  }
                : null}
            {onAddTrack}
            {isAddingTrack}
            {onStartTrack}
        />
        <div
            class="scrollbar-thin overflow-y-auto overflow-x-hidden overscroll-contain px-1"
            style:max-height={`${rowsHeight.height}px`}
            bind:this={listElement}
            data-testid="object-track-list"
        >
            {#each visible.visibleTracks as track (`${track.object_track_id}-${track.annotation_source_id}`)}
                <TrackTimelineRow
                    {ticks}
                    {track}
                    isSelected={selectedTrackKey?.object_track_id === track.object_track_id &&
                        selectedTrackKey.annotation_source_id === track.annotation_source_id}
                    onSelectPosition={selectTrackPosition}
                    onExtend={onExtendTrack}
                    {onExtendStart}
                    {onExtendEnd}
                    onRequestDelete={onDeleteTrack ? requestDelete : undefined}
                />
            {/each}
        </div>
    </div>
    {#if trackToDelete && onDeleteTrack}
        <DeleteTrackDialog
            bind:open={isDeleteDialogOpen}
            trackLabel={`${trackToDelete.annotation_label_name} · Track ${trackToDelete.object_track_number}`}
            annotationCount={trackToDelete.annotations.length}
            onConfirm={() => onDeleteTrack(trackToDelete as SequenceTrackView)}
        />
    {/if}
{/if}
