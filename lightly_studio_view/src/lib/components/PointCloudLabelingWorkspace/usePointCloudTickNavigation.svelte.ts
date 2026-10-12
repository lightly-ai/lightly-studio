import type { PointCloudWorkspaceContext } from './provider/types';

interface Params {
    getWorkspace: () => PointCloudWorkspaceContext;
    getTickNumber: () => number;
    getOnTickChange: () => (tickNumber: number) => void;
}

export function usePointCloudTickNavigation({
    getWorkspace,
    getTickNumber,
    getOnTickChange
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

    $effect(() => {
        const workspace = getWorkspace();
        if (!workspace.isPlaying) return;
        const intervalMs = workspace.playbackIntervalMs;
        const ticks = workspace.ticks;
        const currentTick = workspace.currentTick;

        // Do not outrun the frame queries. While a query key changes, TanStack keeps the
        // previous frame as placeholder data; advancing again in that state can continually
        // replace the request before it completes and leave the scene on the last settled frame.
        if (
            workspace.tickDetails.isFetching ||
            workspace.cloudPointFrame.isFetching ||
            workspace.tickDetails.isPlaceholderData ||
            (workspace.cloudPointFrame.isPlaceholderData &&
                workspace.cloudPointFrame.isEnabled)
        ) {
            return;
        }

        const activeIndex = ticks.findIndex((tick) => tick.seq_number === currentTick);
        const timeout = setTimeout(() => {
            if (activeIndex >= ticks.length - 1) {
                workspace.togglePlayback();
                return;
            }
            goToNextFrame();
        }, intervalMs);
        return () => clearTimeout(timeout);
    });

    return { goToPreviousFrame, goToNextFrame, goToFrame, togglePlayback };
}
