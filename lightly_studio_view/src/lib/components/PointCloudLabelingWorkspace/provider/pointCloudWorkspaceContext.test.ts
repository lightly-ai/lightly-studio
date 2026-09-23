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

const createContext = (statusOverride?: 'loading' | 'unsupported' | 'empty' | 'error'): Context => {
    let context: Context | undefined;
    render(PointCloudWorkspaceContextHarness, {
        datasetId: 'dataset-1',
        sequenceId: 'seq-1',
        statusOverride,
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

    it.each<[Partial<typeof summaryState>, string]>([
        [{}, 'empty'],
        [{ isLoading: true }, 'loading'],
        [{ isError: true }, 'error'],
        [{ data: { ...summaryWithChannels, lidar_channels: [] } }, 'empty'],
        [{ data: summaryWithChannels }, 'ready']
    ])('derives status %s from the summary', (patch, expected) => {
        Object.assign(summaryState, patch);
        expect(createContext().status).toBe(expected);
    });

    it('honors the status override regardless of the summary', () => {
        summaryState.data = summaryWithChannels;
        expect(createContext('unsupported').status).toBe('unsupported');
    });

    it('exposes the summary channels, or empty arrays without data', () => {
        expect(createContext().lidarChannels).toEqual([]);
        expect(createContext().cameraChannels).toEqual([]);

        summaryState.data = summaryWithChannels;
        const context = createContext();
        expect(context.lidarChannels).toHaveLength(1);
        expect(context.cameraChannels[0].group_component_name).toBe('front');
    });

    it('advances and rewinds within bounds, clamped at both ends', () => {
        const context = createContext();
        expect(context.currentTick).toBe(0);
        expect(context.isPlaying).toBe(false);
        expect(context.ticks).toHaveLength(24);

        // Clamped at the first tick.
        context.goToPreviousFrame();
        context.goToNextFrame();
        flushSync();
        expect(context.currentTick).toBe(1);

        // Clamped at the last tick.
        for (let i = 0; i < 30; i += 1) context.goToNextFrame();
        flushSync();
        expect(context.currentTick).toBe(context.ticks.length - 1);
    });

    it('toggles playback', () => {
        const context = createContext();
        context.togglePlayback();
        flushSync();
        expect(context.isPlaying).toBe(true);
    });

    it('retry re-fetches the summary', () => {
        createContext().retry();
        expect(refetch).toHaveBeenCalledOnce();
    });
});
