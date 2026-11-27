<script lang="ts">
    import type { ComponentProps } from 'svelte';
    import type { TickView } from '$lib/api/lightly_studio_local/types.gen';
    import TimelineTransport from './TimelineTransport.svelte';
    import TimelineBufferStatus from '../TimelineBufferStatus/TimelineBufferStatus.svelte';

    interface Props {
        ticks: TickView[];
        currentTick: number;
        isPlaying: boolean;
        playbackIntervalMs: number;
        bufferStatus?: ComponentProps<typeof TimelineBufferStatus>['status'];
        bufferEntireSequence: boolean;
        onBufferEntireSequenceChange: (enabled: boolean) => void;
        onPreviousFrame: () => void;
        onNextFrame: () => void;
        onPlayToggle: () => void;
        onPlaybackIntervalChange: (intervalMs: number) => void;
        onPreviousSequence?: () => void;
        onNextSequence?: () => void;
    }

    let {
        ticks,
        currentTick,
        isPlaying,
        playbackIntervalMs,
        bufferStatus,
        bufferEntireSequence,
        onBufferEntireSequenceChange,
        onPreviousFrame,
        onNextFrame,
        onPlayToggle,
        onPlaybackIntervalChange,
        onPreviousSequence,
        onNextSequence
    }: Props = $props();

    const activeIndex = $derived(ticks.findIndex((tick) => tick.seq_number === currentTick));
    const frameLabel = $derived(
        activeIndex >= 0 ? `Frame ${activeIndex + 1} / ${ticks.length}` : 'Frame — / —'
    );
</script>

<TimelineTransport
    {frameLabel}
    {bufferStatus}
    {bufferEntireSequence}
    {onBufferEntireSequenceChange}
    {isPlaying}
    {playbackIntervalMs}
    hasTicks={ticks.length > 0}
    canGoPrevious={activeIndex > 0}
    canGoNext={activeIndex >= 0 && activeIndex < ticks.length - 1}
    {onPreviousFrame}
    {onNextFrame}
    {onPlayToggle}
    {onPlaybackIntervalChange}
    {onPreviousSequence}
    {onNextSequence}
/>
