<script lang="ts">
    import type { TickView } from '$lib/api/lightly_studio_local/types.gen';
    import TimelineTransport from './TimelineTransport/TimelineTransport.svelte';
    import TimelineTracks from './TimelineTracks/TimelineTracks.svelte';

    /**
     * Frame navigation, object tracks and keyframes for the active recording. Placeholder ruler
     * and lanes until frame loading lands; stepping controls disable at the ends of the sequence.
     */
    interface Props {
        /** Sequence ticks (seq number + anchor timestamp). */
        ticks: TickView[];
        /** Seq number of the active tick; drives the frame counter and ruler highlight. */
        currentTick: number;
        /** Whether playback is currently running; toggles the play/pause icon. */
        isPlaying: boolean;
        /** Point-cloud channel names rendered as timeline lanes. */
        lidarChannelNames?: string[];
        /** Image and video channel names rendered as timeline lanes. */
        cameraChannelNames?: string[];
        /** Step to the previous frame. */
        onPreviousFrame: () => void;
        /** Step to the next frame. */
        onNextFrame: () => void;
        /** Toggle playback between playing and paused. */
        onPlayToggle: () => void;
    }

    let {
        ticks,
        currentTick,
        isPlaying,
        lidarChannelNames = [],
        cameraChannelNames = [],
        onPreviousFrame,
        onNextFrame,
        onPlayToggle
    }: Props = $props();

    // Ticks can be sparse, so resolve the active seq number to its array position rather than
    // treating currentTick as an index. -1 when absent, e.g. for an empty sequence.
    const activeIndex = $derived(ticks.findIndex((tick) => tick.seq_number === currentTick));

    const canGoPrevious = $derived(activeIndex > 0);
    const canGoNext = $derived(activeIndex >= 0 && activeIndex < ticks.length - 1);

    const frameLabel = $derived(
        activeIndex >= 0 ? `Frame ${activeIndex + 1} / ${ticks.length}` : 'Frame — / —'
    );

    const lanes = $derived(
        lidarChannelNames.length > 0 || cameraChannelNames.length > 0
            ? [...lidarChannelNames, ...cameraChannelNames]
            : ['Track 1', 'Track 2']
    );
</script>

<div
    class="flex h-full min-h-0 flex-col border-t bg-background"
    data-testid="workspace-frame-timeline"
>
    <TimelineTransport
        {frameLabel}
        {isPlaying}
        hasTicks={ticks.length > 0}
        {canGoPrevious}
        {canGoNext}
        {onPreviousFrame}
        {onNextFrame}
        {onPlayToggle}
    />
    <TimelineTracks {ticks} {currentTick} {lanes} />
</div>
