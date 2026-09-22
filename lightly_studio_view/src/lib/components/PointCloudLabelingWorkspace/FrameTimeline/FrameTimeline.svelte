<script lang="ts">
    import { ChevronLeft, ChevronRight, Pause, Play } from '@lucide/svelte';
    import { Button } from '$lib/components';
    import type { ChannelSummaryView, TickView } from '$lib/api/lightly_studio_local/types.gen';

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
        /** Point-cloud channels rendered as timeline lanes. */
        lidarChannels?: ChannelSummaryView[];
        /** Image and video channels rendered as timeline lanes. */
        cameraChannels?: ChannelSummaryView[];
        /** Step to the previous frame. */
        onPreviousFrame: () => void;
        /** Step to the next frame. */
        onNextFrame: () => void;
        /** Toggle playback between playing and paused. */
        onPlayToggle: () => void;
    }

    const NANOS_PER_SECOND = 1_000_000_000;

    let {
        ticks,
        currentTick,
        isPlaying,
        lidarChannels = [],
        cameraChannels = [],
        onPreviousFrame,
        onNextFrame,
        onPlayToggle
    }: Props = $props();

    const canGoPrevious = $derived(currentTick > 0);
    const canGoNext = $derived(currentTick < ticks.length - 1);

    const lanes = $derived(
        lidarChannels.length > 0 || cameraChannels.length > 0
            ? [...lidarChannels, ...cameraChannels].map((channel) => channel.group_component_name)
            : ['Track 1', 'Track 2']
    );

    /** Anchor the ruler at the first tick that carries a timestamp so labels stay relative. */
    const baseTimestampNs = $derived(
        ticks.find((tick) => tick.timestamp_ns !== null)?.timestamp_ns ?? null
    );

    const formatTickTime = (timestampNs: number | null): string | undefined => {
        if (timestampNs === null || baseTimestampNs === null) return undefined;
        return `${((timestampNs - baseTimestampNs) / NANOS_PER_SECOND).toFixed(2)}s`;
    };
</script>

<div
    class="flex h-full min-h-0 flex-col border-t bg-background"
    data-testid="workspace-frame-timeline"
>
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
                disabled: ticks.length === 0,
                size: 'sm',
                class: 'h-7 w-7 p-0'
            }}
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
        <span class="ml-2 text-xs text-muted-foreground">
            Frame {currentTick + 1} / {ticks.length}
        </span>
    </div>
    <div class="flex min-h-0 flex-1 flex-col gap-1 overflow-auto px-2 py-1.5">
        <div class="flex h-4 shrink-0 items-end gap-px">
            {#each ticks as tick (tick.seq_number)}
                <span
                    class="w-full {tick.seq_number === currentTick
                        ? 'h-4 bg-primary'
                        : tick.seq_number % 5 === 0
                          ? 'h-3 bg-border'
                          : 'h-1.5 bg-border'}"
                    title={formatTickTime(tick.timestamp_ns)}
                ></span>
            {/each}
        </div>
        {#each lanes as lane (lane)}
            <div class="flex items-center gap-2">
                <span class="w-24 shrink-0 truncate text-xs text-muted-foreground">{lane}</span>
                <div class="h-4 flex-1 rounded bg-muted/50"></div>
            </div>
        {/each}
    </div>
</div>
