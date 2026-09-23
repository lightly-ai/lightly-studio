import { render } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import PointCloudWorkspaceContextHarness from './PointCloudWorkspaceContextHarness.svelte';
import type { createPointCloudWorkspaceContext } from './pointCloudWorkspaceContext.svelte';

// The provider wraps useMcapSequenceSummary; stub it so the context can be built without a live
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

type Context = ReturnType<typeof createPointCloudWorkspaceContext>;

const createContext = (
    props: {
        datasetId?: string;
        sequenceId?: string;
        statusOverride?: 'loading' | 'unsupported' | 'empty' | 'error';
    } = {}
): Context => {
    let context: Context | undefined;
    render(PointCloudWorkspaceContextHarness, {
        datasetId: props.datasetId ?? 'dataset-1',
        sequenceId: props.sequenceId ?? 'seq-1',
        statusOverride: props.statusOverride,
        onReady: (ctx: Context) => {
            context = ctx;
        }
    });
    flushSync();
    if (!context) throw new Error('PointCloudWorkspaceContextHarness did not initialize');
    return context;
};

describe('pointCloudWorkspaceContext', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        summaryState.data = undefined;
        summaryState.isLoading = false;
        summaryState.isError = false;
    });

    describe('status', () => {
        it('is empty when the summary has no data', () => {
            expect(createContext().status).toBe('empty');
        });

        it('is loading while the summary is fetching', () => {
            summaryState.isLoading = true;
            expect(createContext().status).toBe('loading');
        });

        it('is error when the summary fails', () => {
            summaryState.isError = true;
            expect(createContext().status).toBe('error');
        });

        it('is empty when the summary has no lidar channels', () => {
            summaryState.data = { ...summaryWithChannels, lidar_channels: [] };
            expect(createContext().status).toBe('empty');
        });

        it('is ready once the summary has lidar channels', () => {
            summaryState.data = summaryWithChannels;
            expect(createContext().status).toBe('ready');
        });

        it('honors the status override regardless of the summary', () => {
            summaryState.data = summaryWithChannels;
            expect(createContext({ statusOverride: 'unsupported' }).status).toBe('unsupported');
        });
    });

    describe('channels', () => {
        it('exposes the summary channels', () => {
            summaryState.data = summaryWithChannels;
            const context = createContext();
            expect(context.lidarChannels).toHaveLength(1);
            expect(context.cameraChannels[0].group_component_name).toBe('front');
        });

        it('falls back to empty arrays without summary data', () => {
            const context = createContext();
            expect(context.lidarChannels).toEqual([]);
            expect(context.cameraChannels).toEqual([]);
        });
    });

    describe('transport', () => {
        it('starts at the first tick, not playing', () => {
            const context = createContext();
            expect(context.currentTick).toBe(0);
            expect(context.isPlaying).toBe(false);
            expect(context.ticks).toHaveLength(24);
        });

        it('advances and rewinds within bounds', () => {
            const context = createContext();

            context.goToNextFrame();
            flushSync();
            expect(context.currentTick).toBe(1);

            context.goToPreviousFrame();
            flushSync();
            expect(context.currentTick).toBe(0);

            // Clamped at the first tick.
            context.goToPreviousFrame();
            flushSync();
            expect(context.currentTick).toBe(0);
        });

        it('does not advance past the last tick', () => {
            const context = createContext();
            for (let i = 0; i < 30; i += 1) {
                context.goToNextFrame();
            }
            flushSync();
            expect(context.currentTick).toBe(context.ticks.length - 1);
        });

        it('toggles playback', () => {
            const context = createContext();

            context.togglePlayback();
            flushSync();
            expect(context.isPlaying).toBe(true);

            context.togglePlayback();
            flushSync();
            expect(context.isPlaying).toBe(false);
        });
    });

    it('retry re-fetches the summary', () => {
        createContext().retry();
        expect(refetch).toHaveBeenCalledOnce();
    });
});
