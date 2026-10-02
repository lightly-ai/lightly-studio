import { describe, it, expect, vi, beforeEach } from 'vitest';
import { PointCloudWorkspace } from './pointCloudWorkspace.svelte';

// The workspace wraps useMcapSequenceSummary; stub it so the class can be built without a live
// TanStack query client. `summaryState` is mutable so each test drives the derived status/channels.
const {
    summaryState,
    ticksState,
    tickDetailsState,
    refetch,
    ticksRefetch,
    tickRefetch,
    cloudRefetch
} = vi.hoisted(() => ({
    summaryState: { data: undefined, isLoading: false, isError: false } as {
        data: unknown;
        isLoading: boolean;
        isError: boolean;
    },
    tickDetailsState: {
        data: undefined,
        isLoading: false,
        isError: false
    } as {
        data: unknown;
        isLoading: boolean;
        isError: boolean;
    },
    ticksState: {
        data: {
            ticks: [
                { seq_number: 0, timestamp_ns: 10 },
                { seq_number: 4, timestamp_ns: 20 },
                { seq_number: 9, timestamp_ns: 30 }
            ]
        }
    } as {
        data: {
            ticks: Array<{ seq_number: number; timestamp_ns: number }>;
        };
    },
    refetch: vi.fn(),
    ticksRefetch: vi.fn(),
    tickRefetch: vi.fn(),
    cloudRefetch: vi.fn()
}));
const { cloudState, tickDetailsParams } = vi.hoisted(() => ({
    cloudState: { data: undefined } as {
        data: { channels: Array<{ frameId: string }> } | undefined;
    },
    tickDetailsParams: { getTargetFrameId: undefined } as {
        getTargetFrameId?: () => string | undefined;
    }
}));

vi.mock('$lib/hooks/useMcapSequenceSummary/useMcapSequenceSummary', () => ({
    useMcapSequenceSummary: () => ({ summary: summaryState, refetch })
}));
vi.mock('$lib/hooks/useTickDetails/useTickDetails', () => ({
    useTickDetails: (params: { getTargetFrameId?: () => string | undefined }) => {
        tickDetailsParams.getTargetFrameId = params.getTargetFrameId;
        return { tickDetails: { ...tickDetailsState, refetch: tickRefetch } };
    }
}));
vi.mock('$lib/hooks/useMcapSequenceTicks/useMcapSequenceTicks.svelte', () => ({
    useMcapSequenceTicks: () => ({ ticks: ticksState, refetch: ticksRefetch })
}));

vi.mock('$lib/hooks/useCloudPointFrame/useCloudPointFrame.svelte', () => ({
    useCloudPointFrame: () => ({
        query: {
            get data() {
                return cloudState.data;
            },
            isLoading: false,
            isError: false,
            refetch: cloudRefetch
        }
    })
}));

const summaryWithChannels = {
    recording_id: 'rec-1',
    format: 'mcap',
    start_log_time_ns: 0,
    lidar_channels: [{ channel_id: 1, group_component_name: 'lidar', group_component_index: 0 }],
    camera_channels: [{ channel_id: 2, group_component_name: 'front', group_component_index: 0 }]
};

const summaryWithFrames = {
    ...summaryWithChannels,
    reference_frames: [{ name: 'map' }, { name: 'CABIN' }]
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
        tickDetailsState.data = undefined;
        tickDetailsState.isLoading = false;
        tickDetailsState.isError = false;
        cloudState.data = undefined;
    });

    it('defaults to the first reference frame, or none without frames', () => {
        expect(createWorkspace().referenceFrameId).toBe('');

        summaryState.data = summaryWithFrames;
        expect(createWorkspace().referenceFrameId).toBe('map');
    });

    it('selects a known reference frame and ignores an unknown one', () => {
        summaryState.data = summaryWithFrames;
        const workspace = createWorkspace();

        workspace.selectReferenceFrame('CABIN');
        expect(workspace.referenceFrameId).toBe('CABIN');

        workspace.selectReferenceFrame('odom');
        expect(workspace.referenceFrameId).toBe('CABIN');
    });

    it('requests the tick details in the selected reference frame', () => {
        createWorkspace();
        expect(tickDetailsParams.getTargetFrameId?.()).toBeUndefined();

        summaryState.data = summaryWithFrames;
        const workspace = createWorkspace();
        expect(tickDetailsParams.getTargetFrameId?.()).toBe('map');

        workspace.selectReferenceFrame('CABIN');
        expect(tickDetailsParams.getTargetFrameId?.()).toBe('CABIN');
    });

    it('resets the picked reference frame when the sequence changes', () => {
        summaryState.data = summaryWithFrames;
        let sequenceId = $state('seq-1');
        const workspace = new PointCloudWorkspace(() => ({ datasetId: 'dataset-1', sequenceId }));
        workspace.selectReferenceFrame('CABIN');

        sequenceId = 'seq-2';

        expect(workspace.referenceFrameId).toBe('map');
    });

    it.each<[Array<{ frameId: string }>, boolean]>([
        [[{ frameId: 'map' }, { frameId: 'map' }], false],
        [[{ frameId: 'lidar_left' }, { frameId: 'lidar_right' }], true]
    ])('flags a tick shown in the sensor frames %#', (channels, expected) => {
        summaryState.data = summaryWithFrames;
        cloudState.data = { channels };

        expect(createWorkspace().isShowingSensorFrames).toBe(expected);
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

    it('starts on the initial tick when one is given', () => {
        const workspace = new PointCloudWorkspace(() => ({
            datasetId: 'dataset-1',
            sequenceId: 'seq-1',
            initialTick: 3
        }));
        expect(workspace.currentTick).toBe(3);
    });

    it('navigates directly to a requested tick', () => {
        const workspace = createWorkspace();

        workspace.goToFrame(9);

        expect(workspace.currentTick).toBe(9);
    });

    it('advances and rewinds through the ordered ticks, including sparse sequence numbers', () => {
        const workspace = createWorkspace();
        expect(workspace.currentTick).toBe(0);
        expect(workspace.isPlaying).toBe(false);
        expect(workspace.ticks).toEqual(ticksState.data.ticks);

        // Clamped at the first tick.
        workspace.goToPreviousFrame();
        workspace.goToNextFrame();
        expect(workspace.currentTick).toBe(4);

        // Clamped at the last tick.
        workspace.goToNextFrame();
        workspace.goToNextFrame();
        expect(workspace.currentTick).toBe(9);
        workspace.goToPreviousFrame();
        expect(workspace.currentTick).toBe(4);
    });

    it('toggles playback', () => {
        const workspace = createWorkspace();
        workspace.togglePlayback();
        expect(workspace.isPlaying).toBe(true);
    });

    it('retry re-fetches all workspace data when the frame query has usable inputs', () => {
        summaryState.data = summaryWithChannels;
        tickDetailsState.data = {
            recording_id: 'rec-1',
            lidar_channels: { lidar: { channel_id: 1, log_time_ns: '10' } }
        };

        createWorkspace().retry();

        expect(refetch).toHaveBeenCalledOnce();
        expect(ticksRefetch).toHaveBeenCalledOnce();
        expect(tickRefetch).toHaveBeenCalledOnce();
        expect(cloudRefetch).toHaveBeenCalledOnce();
    });

    it('retry does not fetch a frame when no LiDAR channels are selected', () => {
        summaryState.data = summaryWithChannels;
        tickDetailsState.data = {
            recording_id: 'rec-1',
            lidar_channels: { lidar: { channel_id: 1, log_time_ns: '10' } }
        };
        const workspace = new PointCloudWorkspace(() => ({
            datasetId: 'dataset-1',
            sequenceId: 'seq-1',
            selectedLidarChannels: []
        }));

        workspace.retry();

        expect(refetch).toHaveBeenCalledOnce();
        expect(ticksRefetch).toHaveBeenCalledOnce();
        expect(tickRefetch).toHaveBeenCalledOnce();
        expect(cloudRefetch).not.toHaveBeenCalled();
    });
});
