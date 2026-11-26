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
    import { MultiSelectPopover } from '$lib/components/MultiSelectPopover';
    import { WorkspacePanel } from '../../WorkspacePanel';
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
        /** Whether the object tracks panel shows. */
        showObjectTracks?: boolean;
        /** Hides the object tracks panel; the panel shows no close button without it. */
        onHideObjectTracks?: () => void;
        /** Whether the frame tag tracks panel shows. */
        showFrameTags?: boolean;
        /** Hides the frame tag tracks panel; the panel shows no close button without it. */
        onHideFrameTags?: () => void;
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
        showObjectTracks = true,
        onHideObjectTracks,
        showFrameTags = false,
        onHideFrameTags,
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
    const hasRows = $derived(
        (showObjectTracks && tracks.length > 0) || (showFrameTags && frameTags.length > 0)
    );
    // Fills the timeline viewport, so the header keeps its place while a zoomed timeline scrolls.
    const STICKY_HEADER_CLASS = 'sticky left-0 w-[var(--timeline-viewport-width)]';
    // Sticks under the ruler (`h-8`) and the resize handle (`h-2`) when it is shown.
    const stickyTopClass = $derived(hasRows ? 'top-10' : 'top-8');
    // A stored choice can hold ids of removed rows; they must not count as selected.
    const keepListedIds = (ids: string[], items: { value: string }[]) =>
        ids.filter((id) => items.some((item) => item.value === id));
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

{#if showObjectTracks || showFrameTags}
    {#if hasRows}
        <TrackRowsResizer {rowsHeight} getRenderedHeight={getRowsRenderedHeight} />
    {/if}
    {#if showFrameTags}
        <WorkspacePanel
            title="Frame tag tracks"
            onHide={onHideFrameTags}
            headerClass={STICKY_HEADER_CLASS}
            class="w-full border-t px-2 pb-1"
            testId="frame-tag-rows"
        >
            {#snippet actions()}
                {#if frameTags.length > 0}
                    <MultiSelectPopover
                        items={tagItems}
                        selectedIds={keepListedIds(visibleTags.selectedIds, tagItems)}
                        onChange={visibleTags.setSelection}
                        label={`Showing ${visibleTags.visibleTags.length} of ${tagItems.length} tags`}
                        itemNoun="tag"
                        itemNounPlural="tags"
                        showSelectAll
                        triggerClass="h-6 gap-1 px-2"
                        testId="tag-visibility-select"
                    />
                {/if}
            {/snippet}
            <TagTimelineRows {ticks} tags={visibleTags.visibleTags} {onSelectTick} />
        </WorkspacePanel>
    {/if}
    {#if showObjectTracks}
        <WorkspacePanel
            title="Object tracks"
            onHide={onHideObjectTracks}
            headerClass="{STICKY_HEADER_CLASS} z-20 {stickyTopClass}"
            class="w-full border-t px-2 pb-1"
            testId="object-track-rows"
        >
            {#snippet actions()}
                <TrackTimelineToolbar
                    trackVisibility={tracks.length > 0
                        ? {
                              items: trackItems,
                              visibleCount: visible.visibleTracks.length,
                              selectedIds: keepListedIds(visible.selectedKeys, trackItems),
                              onChange: visible.setSelection
                          }
                        : null}
                    {onAddTrack}
                    {isAddingTrack}
                    {onStartTrack}
                />
            {/snippet}
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
        </WorkspacePanel>
    {/if}
    {#if trackToDelete && onDeleteTrack}
        <DeleteTrackDialog
            bind:open={isDeleteDialogOpen}
            trackLabel={`${trackToDelete.annotation_label_name} · Track ${trackToDelete.object_track_number}`}
            annotationCount={trackToDelete.annotations.length}
            onConfirm={() => onDeleteTrack(trackToDelete as SequenceTrackView)}
        />
    {/if}
{/if}
