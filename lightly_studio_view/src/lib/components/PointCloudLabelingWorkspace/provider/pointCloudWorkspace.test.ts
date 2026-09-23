import { describe, it, expect, vi, beforeEach } from 'vitest';
import { PointCloudWorkspace } from './pointCloudWorkspace.svelte';

// The workspace wraps useMcapSequenceSummary; stub it so the class can be built without a live
// TanStack query client. `summaryState` is mutable so each test drives the derived status/channels.
const { summaryState, refetch } = vi.hoisted(() => ({
    summaryState: { data: undefined, isLoading: false, isError: false } as {
        data: unknown;
        isLoading: boolean;
        isError: boolean;
    },
    refetch: vi.fn()
}));

vi.mock('$lib/hooks/useMcapSequenceSummary/useMcapSequenceSummary', () => ({
    useMcapSequenceSummary: () => ({ summary: summaryState, refetch })
}));

const summaryWithChannels = {
    recording_id: 'rec-1',
    format: 'mcap',
    start_log_time_ns: 0,
    lidar_channels: [{ channel_id: 1, group_component_name: 'lidar', group_component_index: 0 }],
    camera_channels: [{ channel_id: 2, group_component_name: 'front', group_component_index: 0 }]
};

const createWorkspace = (statusOverride?: 'loading' | 'unsupported' | 'empty' | 'error') =>
    new PointCloudWorkspace(() => ({
        datasetId: 'dataset-1',
        sequenceId: 'seq-1',
        statusOverride
    }));

describe('PointCloudWorkspace', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        summaryState.data = undefined;
        summaryState.isLoading = false;
        summaryState.isError = false;
    });

    it('exposes the inputs it was built with', () => {
        const workspace = createWorkspace();
        expect(workspace.datasetId).toBe('dataset-1');
        expect(workspace.sequenceId).toBe('seq-1');
    });

    it.each<[Partial<typeof summaryState>, string]>([
        [{}, 'empty'],
        [{ isLoading: true }, 'loading'],
        [{ isError: true }, 'error'],
        [{ data: { ...summaryWithChannels, lidar_channels: [] } }, 'empty'],
        [{ data: summaryWithChannels }, 'ready']
    ])('derives status %s from the summary', (patch, expected) => {
        Object.assign(summaryState, patch);
        expect(createWorkspace().status).toBe(expected);
    });

    it('honors the status override regardless of the summary', () => {
        summaryState.data = summaryWithChannels;
        expect(createWorkspace('unsupported').status).toBe('unsupported');
    });

    it('exposes the summary channels, or empty arrays without data', () => {
        expect(createWorkspace().lidarChannels).toEqual([]);
        expect(createWorkspace().cameraChannels).toEqual([]);

        summaryState.data = summaryWithChannels;
        const workspace = createWorkspace();
        expect(workspace.lidarChannels).toHaveLength(1);
        expect(workspace.cameraChannels[0].group_component_name).toBe('front');
    });

    it('advances and rewinds within bounds, clamped at both ends', () => {
        const workspace = createWorkspace();
        expect(workspace.currentTick).toBe(0);
        expect(workspace.isPlaying).toBe(false);
        expect(workspace.ticks).toHaveLength(24);

        // Clamped at the first tick.
        workspace.goToPreviousFrame();
        workspace.goToNextFrame();
        expect(workspace.currentTick).toBe(1);

        // Clamped at the last tick.
        for (let i = 0; i < 30; i += 1) workspace.goToNextFrame();
        expect(workspace.currentTick).toBe(workspace.ticks.length - 1);
    });

    it('toggles playback', () => {
        const workspace = createWorkspace();
        workspace.togglePlayback();
        expect(workspace.isPlaying).toBe(true);
    });

    it('retry re-fetches the summary', () => {
        createWorkspace().retry();
        expect(refetch).toHaveBeenCalledOnce();
    });
});
