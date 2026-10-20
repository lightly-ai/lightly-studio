import { onDestroy } from 'svelte';
import type { PointCloudWorkspaceContext } from './provider/types';

interface Params {
    getWorkspace: () => PointCloudWorkspaceContext;
    getTickNumber: () => number;
    getOnTickChange: () => (tickNumber: number) => void;
    /** Returns whether a tick has finished prefetching. */
    getIsTickBuffered?: (index: number) => boolean;
}

export function usePointCloudTickNavigation({
    getWorkspace,
    getTickNumber,
    getOnTickChange,
    getIsTickBuffered = () => true
}: Params) {
    const goToPreviousFrame = () => {
        const workspace = getWorkspace();
        workspace.goToPreviousFrame();
        getOnTickChange()(workspace.currentTick + 1);
    };
    const goToNextFrame = () => {
        const workspace = getWorkspace();
        workspace.goToNextFrame();
        getOnTickChange()(workspace.currentTick + 1);
    };
    const goToFrame = (seqNumber: number) => {
        const workspace = getWorkspace();
        // A seek while playing must restart the interval from the selected frame instead of
        // allowing the timer created for the previous frame to fire.
        clearPlaybackTimer();
        scheduledTick = undefined;
        workspace.goToFrame(seqNumber);
        getOnTickChange()(seqNumber + 1);
    };
    const togglePlayback = () => {
        const workspace = getWorkspace();
        const startsAtLastTick =
            !workspace.isPlaying && workspace.currentTick === workspace.ticks.at(-1)?.seq_number;
        workspace.togglePlayback();
        if (startsAtLastTick) getOnTickChange()(workspace.currentTick + 1);
    };

    $effect(() => getWorkspace().goToFrame(getTickNumber() - 1));

    $effect(() => {
        const workspace = getWorkspace();
        const ticks = workspace.ticks;
        const currentTick = workspace.currentTick;
        if (workspace.status !== 'ready' || ticks.length === 0) return;
        if (ticks.some((tick) => tick.seq_number === currentTick)) return;
        workspace.goToFrame(
            ticks.reduce((closest, tick) =>
                Math.abs(tick.seq_number - currentTick) < Math.abs(closest.seq_number - currentTick)
                    ? tick
                    : closest
            ).seq_number
        );
    });

    // Only a change in readiness should restart playback. Other buffered ticks finishing
    // must not repeatedly cancel the timeout for an already-ready next tick.
    const canAdvance = $derived.by(() => {
        const workspace = getWorkspace();
        const activeIndex = workspace.ticks.findIndex(
            (tick) => tick.seq_number === workspace.currentTick
        );
        if (activeIndex < 0) return false;
        const details = workspace.tickDetails;
        const cloud = workspace.cloudPointFrame;
        if (details.isPending || details.isError || details.isPlaceholderData) return false;
        if (cloud.isEnabled && (cloud.isPending || cloud.isError || cloud.isPlaceholderData)) {
            return false;
        }
        const nextIndex = activeIndex + 1;
        return nextIndex >= workspace.ticks.length || getIsTickBuffered(nextIndex);
    });

    let timeout: ReturnType<typeof setTimeout> | undefined;
    let scheduledTick: number | undefined;
    let scheduledInterval: number | undefined;
    const clearPlaybackTimer = () => {
        clearTimeout(timeout);
        timeout = undefined;
    };
    onDestroy(clearPlaybackTimer);

    $effect(() => {
        const workspace = getWorkspace();
        if (!workspace.isPlaying || !canAdvance) {
            clearPlaybackTimer();
            return;
        }
        const intervalMs = workspace.playbackIntervalMs;
        const ticks = workspace.ticks;
        const currentTick = workspace.currentTick;

        if (
            timeout !== undefined &&
            scheduledTick === currentTick &&
            scheduledInterval === intervalMs
        ) {
            return;
        }
        clearPlaybackTimer();
        scheduledTick = currentTick;
        scheduledInterval = intervalMs;
        const activeIndex = ticks.findIndex((tick) => tick.seq_number === currentTick);
        timeout = setTimeout(() => {
            timeout = undefined;
            if (activeIndex >= ticks.length - 1) {
                workspace.togglePlayback();
                return;
            }
            goToNextFrame();
        }, intervalMs);
    });

    return { goToPreviousFrame, goToNextFrame, goToFrame, togglePlayback };
}
