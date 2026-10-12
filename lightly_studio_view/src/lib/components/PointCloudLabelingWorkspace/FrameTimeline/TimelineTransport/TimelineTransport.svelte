<script lang="ts">
    import { ChevronLeft, ChevronRight, Pause, Play, SkipBack, SkipForward } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import { Select } from '$lib/components/Select';

    /** Playback interval at 1x speed, i.e. 10 Hz. */
    const BASE_INTERVAL_MS = 100;
    /** Item values are the interval multiplier relative to 1x (0.2x speed is 5x the interval). */
    const speedItems = [0.1, 0.2, 0.5, 0.8, 1].map((speed) => ({
        value: String(1 / speed),
        label: `${speed}×`
    }));

    /**
     * Transport controls (sequence and frame step, play/pause) and the frame counter for the
     * timeline.
     */
    interface Props {
        /** One-based `Frame n / total`, or an em-dash placeholder when the sequence is empty. */
        frameLabel: string;
        /** Whether playback is currently running; toggles the play/pause icon. */
        isPlaying: boolean;
        playbackIntervalMs: number;
        /** Whether the sequence has any ticks; disables playback when it has none. */
        hasTicks: boolean;
        /** Whether stepping to the previous frame is possible. */
        canGoPrevious: boolean;
        /** Whether stepping to the next frame is possible. */
        canGoNext: boolean;
        /** Step to the previous frame. */
        onPreviousFrame: () => void;
        /** Step to the next frame. */
        onNextFrame: () => void;
        /** Toggle playback between playing and paused. */
        onPlayToggle: () => void;
        onPlaybackIntervalChange: (intervalMs: number) => void;
        /** Open the previous sequence; the control is disabled when absent. */
        onPreviousSequence?: () => void;
        /** Open the next sequence; the control is disabled when absent. */
        onNextSequence?: () => void;
    }

    let {
        frameLabel,
        isPlaying,
        playbackIntervalMs,
        hasTicks,
        canGoPrevious,
        canGoNext,
        onPreviousFrame,
        onNextFrame,
        onPlayToggle,
        onPlaybackIntervalChange,
        onPreviousSequence,
        onNextSequence
    }: Props = $props();
</script>

<div class="flex shrink-0 items-center gap-1 border-b px-2 py-1">
    <Button
        variant="ghost"
        icon={SkipBack}
        ariaLabel="Previous sequence"
        buttonProps={{
            onclick: onPreviousSequence,
            disabled: !onPreviousSequence,
            size: 'sm',
            class: 'h-7 w-7 p-0'
        }}
    />
    <Button
        variant="ghost"
        icon={ChevronLeft}
        ariaLabel="Previous frame"
        buttonProps={{
            onclick: onPreviousFrame,
            disabled: !canGoPrevious,
            size: 'sm',
            class: 'h-7 w-7 p-0'
        }}
    />
    <Button
        variant="ghost"
        icon={isPlaying ? Pause : Play}
        ariaLabel={isPlaying ? 'Pause frames' : 'Play frames'}
        buttonProps={{
            onclick: onPlayToggle,
            disabled: !hasTicks,
            size: 'sm',
            class: 'h-7 w-7 p-0'
        }}
    />
    <Select
        items={speedItems}
        value={String(playbackIntervalMs / BASE_INTERVAL_MS)}
        size="xs"
        variant="ghost"
        class="ml-1 h-7 w-auto"
        testId="playback-speed-select"
        selectProps={{ 'aria-label': 'Playback speed' }}
        onValueChange={(slowdown) => onPlaybackIntervalChange(BASE_INTERVAL_MS * Number(slowdown))}
    />
    <Button
        variant="ghost"
        icon={ChevronRight}
        ariaLabel="Next frame"
        buttonProps={{
            onclick: onNextFrame,
            disabled: !canGoNext,
            size: 'sm',
            class: 'h-7 w-7 p-0'
        }}
    />
    <Button
        variant="ghost"
        icon={SkipForward}
        ariaLabel="Next sequence"
        buttonProps={{
            onclick: onNextSequence,
            disabled: !onNextSequence,
            size: 'sm',
            class: 'h-7 w-7 p-0'
        }}
    />
    <span class="ml-2 text-xs text-muted-foreground">{frameLabel}</span>
</div>
