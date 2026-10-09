<script lang="ts">
    import type { TickView } from '$lib/api/lightly_studio_local/types.gen';
    import TimelineTransport from './TimelineTransport/TimelineTransport.svelte';
    import TimelineTracks from './TimelineTracks/TimelineTracks.svelte';

    /**
     * Frame navigation for the active recording with a tick ruler; stepping controls disable at
     * the ends of the sequence.
     */
    interface Props {
        /** Sequence ticks (seq number + anchor timestamp). */
        ticks: TickView[];
        /** Seq number of the active tick; drives the frame counter and ruler highlight. */
        currentTick: number;
        /** Whether playback is currently running; toggles the play/pause icon. */
        isPlaying: boolean;
        playbackIntervalMs: number;
        /** Step to the previous frame. */
        onPreviousFrame: () => void;
        /** Step to the next frame. */
        onNextFrame: () => void;
        /** Toggle playback between playing and paused. */
        onPlayToggle: () => void;
        onPlaybackIntervalChange: (intervalMs: number) => void;
        onSelectTick: (seqNumber: number) => void;
        /** Open the previous sequence; the control is disabled when absent. */
        onPreviousSequence?: () => void;
        /** Open the next sequence; the control is disabled when absent. */
        onNextSequence?: () => void;
    }

    let {
        ticks,
        currentTick,
        isPlaying,
        playbackIntervalMs,
        onPreviousFrame,
        onNextFrame,
        onPlayToggle,
        onPlaybackIntervalChange,
        onSelectTick,
        onPreviousSequence,
        onNextSequence
    }: Props = $props();

    // Ticks can be sparse, so resolve the active seq number to its array position rather than
    // treating currentTick as an index. -1 when absent, e.g. for an empty sequence.
    const activeIndex = $derived(ticks.findIndex((tick) => tick.seq_number === currentTick));

    const canGoPrevious = $derived(activeIndex > 0);
    const canGoNext = $derived(activeIndex >= 0 && activeIndex < ticks.length - 1);

    const frameLabel = $derived(
        activeIndex >= 0 ? `Frame ${activeIndex + 1} / ${ticks.length}` : 'Frame — / —'
    );
</script>

<div
    class="flex h-full min-h-0 flex-col border-t bg-background"
    data-testid="workspace-frame-timeline"
>
    <TimelineTransport
        {frameLabel}
        {isPlaying}
        {playbackIntervalMs}
        hasTicks={ticks.length > 0}
        {canGoPrevious}
        {canGoNext}
        {onPreviousFrame}
        {onNextFrame}
        {onPlayToggle}
        {onPlaybackIntervalChange}
        {onPreviousSequence}
        {onNextSequence}
    />
    <TimelineTracks {ticks} {currentTick} {onSelectTick} />
</div>
