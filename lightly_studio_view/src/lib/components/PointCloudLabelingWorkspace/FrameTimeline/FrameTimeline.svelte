<script lang="ts">
    import type { SequenceTrackView, TickView } from '$lib/api/lightly_studio_local/types.gen';
    import TimelineContent from './TimelineContent/TimelineContent.svelte';
    import TimelineTransportControls from './TimelineTransport/TimelineTransportControls.svelte';

    interface BufferRange {
        /** Inclusive zero-based index of the first buffered tick. */
        startIndex: number;
        /** Inclusive zero-based index of the last buffered tick. */
        endIndex: number;
    }

    /** Playback controls and annotation tracks for the active recording. */
    interface Props {
        /** Sequence ticks (seq number + anchor timestamp). */
        ticks: TickView[];
        tracks?: SequenceTrackView[];
        selectedAnnotationId?: string | null;
        /** Seq number of the active tick; drives the frame counter and ruler highlight. */
        currentTick: number;
        /** Whether playback is currently running; toggles the play/pause icon. */
        isPlaying: boolean;
        playbackIntervalMs: number;
        /** Whether the complete sequence should be prefetched. */
        bufferEntireSequence: boolean;
        /** Called when the complete-sequence buffering option changes. */
        onBufferEntireSequenceChange: (enabled: boolean) => void;
        /** Inclusive tick-index ranges whose data is ready for playback. */
        bufferedRanges: readonly BufferRange[];
        /** Step to the previous frame. */
        onPreviousFrame: () => void;
        /** Step to the next frame. */
        onNextFrame: () => void;
        /** Toggle playback between playing and paused. */
        onPlayToggle: () => void;
        onPlaybackIntervalChange: (intervalMs: number) => void;
        onSelectTick: (seqNumber: number) => void;
        onSelectAnnotation?: (annotationId: string) => void;
        /** Starts a track from the selected cuboid; set only while that is possible. */
        onStartTrack?: () => void;
        /** Called when the user starts dragging the slider. */
        onSeekStart?: () => void;
        /** Called when the user releases the slider. */
        onSeekEnd?: () => void;
        /** Open the previous sequence; the control is disabled when absent. */
        onPreviousSequence?: () => void;
        /** Open the next sequence; the control is disabled when absent. */
        onNextSequence?: () => void;
    }

    let {
        ticks,
        tracks = [],
        selectedAnnotationId = null,
        currentTick,
        isPlaying,
        playbackIntervalMs,
        bufferEntireSequence,
        onBufferEntireSequenceChange,
        bufferedRanges,
        onPreviousFrame,
        onNextFrame,
        onPlayToggle,
        onPlaybackIntervalChange,
        onSelectTick,
        onSelectAnnotation = () => {},
        onStartTrack,
        onSeekStart,
        onSeekEnd,
        onPreviousSequence,
        onNextSequence
    }: Props = $props();
</script>

<div class="flex min-h-0 flex-col border-t bg-background" data-testid="workspace-frame-timeline">
    <TimelineTransportControls
        {ticks}
        {currentTick}
        {bufferEntireSequence}
        {onBufferEntireSequenceChange}
        {isPlaying}
        {playbackIntervalMs}
        {onPreviousFrame}
        {onNextFrame}
        {onPlayToggle}
        {onPlaybackIntervalChange}
        {onPreviousSequence}
        {onNextSequence}
    />
    <TimelineContent
        {ticks}
        {tracks}
        {currentTick}
        {selectedAnnotationId}
        {bufferedRanges}
        {onSelectTick}
        {onSelectAnnotation}
        {onStartTrack}
        {onSeekStart}
        {onSeekEnd}
    />
</div>
