import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { PointCloudWorkspace } from './pointCloudWorkspace.svelte';

// The workspace wraps useMcapSequenceSummary; stub it so the class can be built without a live
// TanStack query client. `summaryState` is mutable so each test drives the derived status/channels.
const {
    summaryState,
    ticksState,
    tickQuery,
    cloudQuery,
    refetch,
    ticksRefetch,
    tickRefetch,
    cloudRefetch,
    cloudParams
} = vi.hoisted(() => {
    const tickRefetch = vi.fn();
    const cloudRefetch = vi.fn();
    return {
        summaryState: { data: undefined, isLoading: false, isError: false } as {
            data: unknown;
            isLoading: boolean;
            isError: boolean;
        },
        ticksState: { data: undefined } as { data: unknown },
        // Live query objects, so a test can mark a frame as still loading.
        tickQuery: {
            data: undefined,
            isLoading: false,
            isError: false,
            isFetching: false,
            refetch: tickRefetch
        },
        cloudQuery: {
            data: undefined,
            isLoading: false,
            isError: false,
            isFetching: false,
            isPlaceholderData: false,
            refetch: cloudRefetch
        },
        refetch: vi.fn(),
        ticksRefetch: vi.fn(),
        tickRefetch,
        cloudRefetch,
        // The latest params getter the workspace handed to useCloudPointFrame.
        cloudParams: { get: undefined as undefined | (() => { targetFrameId?: string }) }
    };
});

vi.mock('$lib/hooks/useMcapSequenceSummary/useMcapSequenceSummary', () => ({
    useMcapSequenceSummary: () => ({ summary: summaryState, refetch })
}));
vi.mock('$lib/hooks/useSequenceTicks/useSequenceTicks', () => ({
    useSequenceTicks: () => ({ sequenceTicks: { ...ticksState, refetch: ticksRefetch } })
}));
vi.mock('$lib/hooks/useTickDetails/useTickDetails', () => ({
    useTickDetails: () => ({ tickDetails: tickQuery })
}));
vi.mock('$lib/hooks/useCloudPointFrame/useCloudPointFrame.svelte', () => ({
    useCloudPointFrame: (getParams: () => { targetFrameId?: string }) => {
        cloudParams.get = getParams;
        return { query: cloudQuery };
    }
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
        ticksState.data = undefined;
        tickQuery.isFetching = false;
        cloudQuery.isFetching = false;
        cloudQuery.isPlaceholderData = false;
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.useRealTimers();
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

    it('shows every lidar channel by default and toggles them individually', () => {
        summaryState.data = {
            ...summaryWithChannels,
            lidar_channels: [
                { channel_id: 1, group_component_name: 'lidar_left', group_component_index: 0 },
                { channel_id: 3, group_component_name: 'lidar_right', group_component_index: 1 }
            ]
        };
        const workspace = createWorkspace();
        expect(workspace.selectedLidarChannels).toEqual([1, 3]);

        workspace.toggleLidarChannel(1);
        expect(workspace.selectedLidarChannels).toEqual([3]);

        workspace.toggleLidarChannel(1);
        expect(workspace.selectedLidarChannels).toEqual([3, 1]);
    });

    it('aligns the point clouds in the cabin frame', () => {
        summaryState.data = {
            ...summaryWithChannels,
            lidar_channels: [
                {
                    channel_id: 1,
                    group_component_name: 'lidar_left',
                    group_component_index: 0,
                    frame_id: 'livox_front_left'
                },
                {
                    channel_id: 3,
                    group_component_name: 'lidar_right',
                    group_component_index: 1,
                    frame_id: 'livox_rear_left'
                }
            ]
        };
        const workspace = createWorkspace();
        workspace.toggleLidarChannel(1);
        expect(cloudParams.get?.().targetFrameId).toBe('CABIN');
    });

    it('starts on the initial tick when one is given', () => {
        const workspace = new PointCloudWorkspace(() => ({
            datasetId: 'dataset-1',
            sequenceId: 'seq-1',
            initialTick: 3
        }));
        expect(workspace.currentTick).toBe(3);
    });

    it('steps through the sequence ticks, clamped at both ends', () => {
        // Sparse ticks: stepping moves by position in the list, not by seq number.
        ticksState.data = {
            ticks: [
                { seq_number: 0, timestamp_ns: 100 },
                { seq_number: 2, timestamp_ns: 300 },
                { seq_number: 5, timestamp_ns: 600 }
            ]
        };
        const workspace = createWorkspace();
        expect(workspace.ticks).toHaveLength(3);

        workspace.goToPreviousFrame();
        expect(workspace.currentTick).toBe(0);

        workspace.goToNextFrame();
        expect(workspace.currentTick).toBe(2);

        workspace.goToNextFrame();
        workspace.goToNextFrame();
        expect(workspace.currentTick).toBe(5);

        workspace.goToPreviousFrame();
        expect(workspace.currentTick).toBe(2);
    });

    it('steps and toggles playback when the handlers are called without the instance', () => {
        ticksState.data = {
            ticks: [
                { seq_number: 0, timestamp_ns: 100 },
                { seq_number: 1, timestamp_ns: 200 }
            ]
        };
        const workspace = createWorkspace();
        // The panes receive the handlers as plain callbacks, e.g. `onNextFrame={workspace.goToNextFrame}`.
        const { goToNextFrame, goToPreviousFrame, togglePlayback } = workspace;

        goToNextFrame();
        expect(workspace.currentTick).toBe(1);
        goToPreviousFrame();
        expect(workspace.currentTick).toBe(0);
        togglePlayback();
        expect(workspace.isPlaying).toBe(true);
    });

    it('plays through the ticks and stops at the last one', () => {
        ticksState.data = {
            ticks: [0, 1, 2].map((seq) => ({ seq_number: seq, timestamp_ns: seq }))
        };
        const workspace = createWorkspace();

        workspace.togglePlayback();
        vi.advanceTimersToNextFrame();
        expect(workspace.currentTick).toBe(1);

        vi.advanceTimersByTime(200);
        expect(workspace.currentTick).toBe(2);
        expect(workspace.isPlaying).toBe(false);
    });

    it('waits for the current frame to load before playing on', () => {
        ticksState.data = { ticks: [0, 1].map((seq) => ({ seq_number: seq, timestamp_ns: seq })) };
        const workspace = createWorkspace();
        cloudQuery.isFetching = true;

        workspace.togglePlayback();
        vi.advanceTimersByTime(200);
        expect(workspace.currentTick).toBe(0);

        // The fetch is done, but the previous frame is still shown until the new one is set.
        cloudQuery.isFetching = false;
        cloudQuery.isPlaceholderData = true;
        vi.advanceTimersByTime(200);
        expect(workspace.currentTick).toBe(0);

        cloudQuery.isPlaceholderData = false;
        vi.advanceTimersToNextFrame();
        expect(workspace.currentTick).toBe(1);
    });

    it('pauses playback, and restarts from the first tick at the end', () => {
        ticksState.data = { ticks: [0, 1].map((seq) => ({ seq_number: seq, timestamp_ns: seq })) };
        const workspace = createWorkspace();

        workspace.togglePlayback();
        workspace.togglePlayback();
        vi.advanceTimersByTime(200);
        expect(workspace.currentTick).toBe(0);
        expect(workspace.isPlaying).toBe(false);

        workspace.goToNextFrame();
        workspace.togglePlayback();
        expect(workspace.currentTick).toBe(0);
        expect(workspace.isPlaying).toBe(true);
        workspace.dispose();
        expect(workspace.isPlaying).toBe(false);
    });

    it('does not step without ticks', () => {
        const workspace = createWorkspace();
        workspace.goToNextFrame();
        expect(workspace.currentTick).toBe(0);
    });

    it('toggles playback', () => {
        const workspace = createWorkspace();
        workspace.togglePlayback();
        expect(workspace.isPlaying).toBe(true);
    });

    it('retry re-fetches all workspace data', () => {
        createWorkspace().retry();
        expect(refetch).toHaveBeenCalledOnce();
        expect(ticksRefetch).toHaveBeenCalledOnce();
        expect(tickRefetch).toHaveBeenCalledOnce();
        expect(cloudRefetch).toHaveBeenCalledOnce();
    });
});
