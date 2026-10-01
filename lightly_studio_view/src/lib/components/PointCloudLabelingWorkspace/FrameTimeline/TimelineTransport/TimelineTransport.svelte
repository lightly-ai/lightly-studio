<script lang="ts">
    import { ChevronLeft, ChevronRight, Pause, Play } from '@lucide/svelte';
    import { Button } from '$lib/components';

    /** Transport controls (step, play/pause) and the frame counter for the timeline. */
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
        onPlaybackIntervalChange
    }: Props = $props();
</script>

<div class="flex shrink-0 items-center gap-1 border-b px-2 py-1">
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
    <label class="ml-1 flex items-center gap-1 text-xs text-muted-foreground">
        Interval
        <input
            aria-label="Playback interval in seconds"
            class="h-7 w-14 rounded border bg-background px-1 text-foreground"
            type="number"
            min="0.1"
            max="5"
            step="0.1"
            value={playbackIntervalMs / 1000}
            oninput={(event) => {
                const seconds = Number(event.currentTarget.value);
                if (Number.isFinite(seconds)) {
                    onPlaybackIntervalChange(Math.min(5000, Math.max(100, seconds * 1000)));
                }
            }}
        />
        s
    </label>
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
    <span class="ml-2 text-xs text-muted-foreground">{frameLabel}</span>
</div>
