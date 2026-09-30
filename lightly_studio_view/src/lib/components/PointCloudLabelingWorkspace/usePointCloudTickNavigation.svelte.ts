import type { PointCloudWorkspaceContext } from './provider/types';

interface Params {
    workspace: PointCloudWorkspaceContext;
    getTickNumber: () => number;
    getOnTickChange: () => (tickNumber: number) => void;
}

export function usePointCloudTickNavigation({ workspace, getTickNumber, getOnTickChange }: Params) {
    const goToPreviousFrame = () => {
        workspace.goToPreviousFrame();
        getOnTickChange()(workspace.currentTick + 1);
    };
    const goToNextFrame = () => {
        workspace.goToNextFrame();
        getOnTickChange()(workspace.currentTick + 1);
    };

    $effect(() => workspace.goToFrame(getTickNumber() - 1));

    $effect(() => {
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
        if (!workspace.isPlaying) return;
        const intervalMs = workspace.playbackIntervalMs;
        const ticks = workspace.ticks;
        const currentTick = workspace.currentTick;
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

    return { goToPreviousFrame, goToNextFrame };
}
