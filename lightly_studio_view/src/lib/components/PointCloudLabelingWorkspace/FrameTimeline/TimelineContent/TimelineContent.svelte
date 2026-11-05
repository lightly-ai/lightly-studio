<script lang="ts">
    import type { SequenceTrackView, TickView } from '$lib/api/lightly_studio_local/types.gen';
    import TimelineTracks from '../TimelineTracks/TimelineTracks.svelte';
    import TrackTimelineRows from '../TrackTimelineRows/TrackTimelineRows.svelte';

    interface Props {
        ticks: TickView[];
        tracks: SequenceTrackView[];
        currentTick: number;
        selectedAnnotationId: string | null;
        bufferedRanges: ReadonlyArray<{ startIndex: number; endIndex: number }>;
        onSelectTick: (seqNumber: number) => void;
        onSelectAnnotation: (annotationId: string) => void;
        onStartTrack?: () => void;
        onAddTrack?: () => void;
        isAddingTrack?: boolean;
        onDeleteTrack?: (track: SequenceTrackView) => Promise<unknown>;
        sequenceId?: string;
        onExtendTrack?: (
            track: SequenceTrackView,
            startSeqNumber: number,
            endSeqNumber: number
        ) => void;
        onSeekStart?: () => void;
        onSeekEnd?: () => void;
    }

    let {
        ticks,
        tracks,
        currentTick,
        selectedAnnotationId,
        bufferedRanges,
        onSelectTick,
        onSelectAnnotation,
        onStartTrack,
        onAddTrack,
        isAddingTrack = false,
        onExtendTrack,
        onDeleteTrack,
        sequenceId,
        onSeekStart,
        onSeekEnd
    }: Props = $props();
    let previewTick = $state<number | null>(null);
    const visibleTick = $derived(previewTick ?? currentTick);
    const activeIndex = $derived(ticks.findIndex((tick) => tick.seq_number === visibleTick));
</script>

<div class="relative flex-none">
    <TimelineTracks
        {ticks}
        {currentTick}
        {bufferedRanges}
        {onSelectTick}
        onPreviewTick={(seqNumber) => (previewTick = seqNumber)}
        {onSeekStart}
        {onSeekEnd}
    />
    <TrackTimelineRows
        {ticks}
        {tracks}
        {selectedAnnotationId}
        {onSelectAnnotation}
        {onSelectTick}
        {onStartTrack}
        {onAddTrack}
        {isAddingTrack}
        {onExtendTrack}
        {onDeleteTrack}
        {sequenceId}
        onExtendStart={onSeekStart}
        onExtendEnd={onSeekEnd}
    />
    {#if activeIndex >= 0 && ticks.length > 0}
        {@const position = (activeIndex + 0.5) / ticks.length}
        <span
            class="pointer-events-none absolute bottom-1 top-[15px] z-30 w-px bg-primary"
            style:left={`calc(0.5rem + ${position * 100}% - ${position}rem + 7px - ${position * 14}px)`}
            aria-hidden="true"
            data-testid="timeline-playhead"
        ></span>
    {/if}
</div>
