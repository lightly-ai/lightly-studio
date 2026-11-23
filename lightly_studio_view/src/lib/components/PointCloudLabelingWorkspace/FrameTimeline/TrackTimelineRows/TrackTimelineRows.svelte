<script lang="ts">
    import type {
        SequenceTrackView,
        TickTagView,
        TickView
    } from '$lib/api/lightly_studio_local/types.gen';
    import { TagTimelineRows, useVisibleTags } from '../TagTimelineRows';
    import { DeleteTrackDialog } from './DeleteTrackDialog';
    import TrackTimelineRow from './TrackTimelineRow/TrackTimelineRow.svelte';
    import { TrackRowsResizer, useTrackRowsHeight, type TrackRowsHeight } from './TrackRowsResizer';
    import { TrackTimelineToolbar } from './TrackTimelineToolbar';
    import { useVisibleTracks } from './useVisibleTracks.svelte';
    import { getTrackKey } from './visibleTracks';

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
        /** Set while editing: sets a track's coverage to the given tick range. */
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
        showFrameTags?: boolean;
        /** Set when frame tags can be shown: toggles the frame tag rows. */
        onShowFrameTagsChange?: (checked: boolean) => void;
        /** The frame tags of the sequence; the chosen ones show as rows while `showFrameTags` is set. */
        frameTags?: TickTagView[];
        /** The height limit of the rows; the timeline scroll area applies it. */
        rowsHeight?: TrackRowsHeight;
        /** The height the rows currently have on screen. */
        getRowsRenderedHeight?: () => number;
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
        sequenceId,
        showFrameTags = false,
        onShowFrameTagsChange,
        frameTags = [],
        rowsHeight = useTrackRowsHeight(),
        getRowsRenderedHeight
    }: Props = $props();
    const visible = useVisibleTracks({
        getTracks: () => tracks,
        getSelectedAnnotationId: () => selectedAnnotationId,
        getStorageKey: () =>
            sequenceId ? `lightlyStudio_trackTimelineVisibleTracks_${sequenceId}` : undefined
    });
    const visibleTags = useVisibleTags({
        getTags: () => frameTags,
        getStorageKey: () =>
            sequenceId ? `lightlyStudio_frameTimelineVisibleTags_${sequenceId}` : undefined
    });
    const trackItems = $derived(
        tracks.map((track) => ({
            value: getTrackKey(track),
            label: `${track.annotation_label_name} · Track ${track.object_track_number}`
        }))
    );
    const tagItems = $derived(frameTags.map((tag) => ({ value: tag.tag_id, label: tag.name })));
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

{#if tracks.length > 0 || onStartTrack || onAddTrack || onShowFrameTagsChange}
    {#if tracks.length > 0}
        <TrackRowsResizer {rowsHeight} getRenderedHeight={getRowsRenderedHeight} />
    {/if}
    <div class="w-full border-t px-2 pb-1" data-testid="object-track-rows">
        <!-- Sticks under the ruler (`h-8`) and the resize handle (`h-2`) when it is shown. -->
        <div class="sticky z-20 bg-background py-1 {tracks.length > 0 ? 'top-10' : 'top-8'}">
            <TrackTimelineToolbar
                trackVisibility={tracks.length > 0
                    ? {
                          items: trackItems,
                          visibleCount: visible.visibleTracks.length,
                          selectedIds: visible.selectedKeys,
                          onChange: visible.setSelection
                      }
                    : null}
                {onAddTrack}
                {isAddingTrack}
                {onStartTrack}
                frameTags={onShowFrameTagsChange
                    ? { checked: showFrameTags, onCheckedChange: onShowFrameTagsChange }
                    : undefined}
                tagVisibility={showFrameTags && frameTags.length > 0
                    ? {
                          items: tagItems,
                          visibleCount: visibleTags.visibleTags.length,
                          selectedIds: visibleTags.selectedIds,
                          onChange: visibleTags.setSelection
                      }
                    : undefined}
            />
        </div>
        {#if showFrameTags}
            <TagTimelineRows {ticks} tags={visibleTags.visibleTags} {onSelectTick} />
        {/if}
        <div class="w-full px-1" data-testid="object-track-list" data-timeline-body>
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
