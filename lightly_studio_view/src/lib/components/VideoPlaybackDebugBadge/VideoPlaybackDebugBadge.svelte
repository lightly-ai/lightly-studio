<script lang="ts">
    import type { PlaybackSelectionStrategy } from '$lib/utils/frame';
    import type { SelectionModeOverride } from '$lib/components/CanvasVideoPlayer/CanvasVideoPlayer.svelte';

    export interface PlaybackDebugSample {
        clockTime: number;
        currentTime: number;
        mediaTime: number | null;
        sourceTime: number;
        selectedFrameNumber: number | null;
        selectedFrameTimestamp: number | null;
        windowStartTimestamp: number | null;
        windowEndTimestamp: number | null;
        nextFrameTimestamp: number | null;
        renderedFrameNumber: number | null;
        requestedFrameIndex?: number | null;
        resolvedFrameIndex?: number | null;
        pinnedFrameIndex?: number | null;
        inFlightSeekTargetTime?: number | null;
        selectorInvariantHolds: boolean;
        source: 'rvfc' | 'raf' | 'event';
        strategy: PlaybackSelectionStrategy;
        selectionModeOverride?: SelectionModeOverride;
        frameStartFrameNumber?: number | null;
        midpointFrameNumber?: number | null;
    }

    const { sample }: { sample: PlaybackDebugSample | null } = $props();

    const formatNumber = (value: number | null): string => {
        if (value == null) {
            return '-';
        }

        return value.toFixed(6);
    };
    const status = $derived(sample ? (sample.selectorInvariantHolds ? 'ok' : 'fail') : 'waiting');
</script>

<div
    class="pointer-events-none absolute left-2 top-2 z-20 rounded bg-black/80 px-2 py-1 font-mono text-[10px] text-white"
    data-testid="video-playback-debug"
>
    {#if sample}
        <div>src: {sample.source}</div>
        <div>current: {formatNumber(sample.currentTime)}</div>
        <div>media: {formatNumber(sample.mediaTime)}</div>
        <div>used: {formatNumber(sample.sourceTime)}</div>
        <div>mode: {sample.strategy}</div>
        <div>override: {sample.selectionModeOverride ?? 'auto'}</div>
        <div>selected: {sample.selectedFrameNumber ?? '-'}</div>
        <div>selected_ts: {formatNumber(sample.selectedFrameTimestamp)}</div>
        <div>next_ts: {formatNumber(sample.nextFrameTimestamp)}</div>
        <div>window_start: {formatNumber(sample.windowStartTimestamp)}</div>
        <div>window_end: {formatNumber(sample.windowEndTimestamp)}</div>
        <div>rendered: {sample.renderedFrameNumber ?? '-'}</div>
        <div>requested_idx: {sample.requestedFrameIndex ?? '-'}</div>
        <div>resolved_idx: {sample.resolvedFrameIndex ?? '-'}</div>
        <div>pinned_frame: {sample.pinnedFrameIndex ?? '-'}</div>
        <div>seek_target: {formatNumber(sample.inFlightSeekTargetTime ?? null)}</div>
        {#if sample.frameStartFrameNumber != null}
            <div>start_sel: {sample.frameStartFrameNumber}</div>
        {/if}
        {#if sample.midpointFrameNumber != null}
            <div>mid_sel: {sample.midpointFrameNumber}</div>
        {/if}
    {:else}
        <div>src: -</div>
        <div>current: -</div>
        <div>media: -</div>
        <div>used: -</div>
        <div>mode: -</div>
        <div>override: -</div>
        <div>selected: -</div>
        <div>selected_ts: -</div>
        <div>next_ts: -</div>
        <div>window_start: -</div>
        <div>window_end: -</div>
        <div>rendered: -</div>
        <div>requested_idx: -</div>
        <div>resolved_idx: -</div>
        <div>pinned_frame: -</div>
        <div>seek_target: -</div>
    {/if}
    <div>invariant: {status}</div>
</div>
