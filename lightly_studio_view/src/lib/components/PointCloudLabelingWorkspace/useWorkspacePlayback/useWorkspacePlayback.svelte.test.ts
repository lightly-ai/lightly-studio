import { render } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { PointCloudWorkspaceContext } from '../provider/types';
import type { useWorkspacePlayback } from './useWorkspacePlayback.svelte';
import Harness from './UseWorkspacePlaybackHarness.svelte';

const capture = vi.hoisted(() => ({
    params: undefined as
        | {
              getRanges: () => { startIndex: number; endIndex: number }[];
              getRequestId: () => string;
          }
        | undefined
}));

vi.mock('$lib/hooks', () => ({
    useMcapTickPrefetchScheduler: (params: NonNullable<typeof capture.params>) => {
        capture.params = params;
        return { bufferedRanges: [], errors: new Map(), isRetrying: false, retryFailed: vi.fn() };
    }
}));

const defaultOptions = { datasetId: 'dataset', sequenceId: 'sequence', prefetchTickCount: 50 };

function createWorkspace(currentTick: number, tickCount = 120): PointCloudWorkspaceContext {
    return {
        status: 'ready',
        currentTick,
        referenceFrameId: '',
        isPlaying: false,
        ticks: Array.from({ length: tickCount }, (_, seq_number) => ({
            seq_number,
            timestamp_ns: null
        })),
        tickDetails: {},
        cloudPointFrame: {},
        goToFrame: vi.fn(),
        goToNextFrame: vi.fn(),
        goToPreviousFrame: vi.fn(),
        togglePlayback: vi.fn()
    } as unknown as PointCloudWorkspaceContext;
}

describe('useWorkspacePlayback buffering', () => {
    beforeEach(() => {
        sessionStorage.removeItem('lightlyStudio_pointCloudBufferEntireSequence');
        capture.params = undefined;
    });

    it('keeps the window moving after seeking beyond its original range', async () => {
        let playback: ReturnType<typeof useWorkspacePlayback> | undefined;
        const view = render(Harness, {
            workspace: createWorkspace(0),
            options: defaultOptions,
            onReady: (value) => (playback = value)
        });
        flushSync();
        playback?.handleSelectTick(5);
        await view.rerender({ workspace: createWorkspace(55) });

        expect(capture.params?.getRanges()).toEqual([{ startIndex: 55, endIndex: 104 }]);
    });

    it('starts buffering a shorter sequence after seeking in the previous sequence', async () => {
        let playback: ReturnType<typeof useWorkspacePlayback> | undefined;
        const view = render(Harness, {
            workspace: createWorkspace(0),
            options: defaultOptions,
            onReady: (value) => (playback = value)
        });
        flushSync();
        playback?.handleSelectTick(110);
        await view.rerender({
            workspace: createWorkspace(0, 20),
            options: { ...defaultOptions, sequenceId: 'shorter' }
        });

        expect(capture.params?.getRanges()).toEqual([{ startIndex: 0, endIndex: 19 }]);
    });

    it('keeps whole-sequence buffering stable during playback and restarts the window at the playhead', async () => {
        sessionStorage.setItem('lightlyStudio_pointCloudBufferEntireSequence', 'true');
        let playback: ReturnType<typeof useWorkspacePlayback> | undefined;
        const view = render(Harness, {
            workspace: createWorkspace(100),
            options: defaultOptions,
            onReady: (value) => (playback = value)
        });
        flushSync();
        const requestId = capture.params?.getRequestId();
        await view.rerender({ workspace: createWorkspace(110) });
        expect(capture.params?.getRequestId()).toBe(requestId);
        expect(capture.params?.getRanges()).toEqual([
            { startIndex: 100, endIndex: 119 },
            { startIndex: 0, endIndex: 99 }
        ]);

        playback?.setBufferEntireSequence(false);
        flushSync();

        expect(capture.params?.getRanges()).toEqual([{ startIndex: 110, endIndex: 119 }]);
    });

    it('resets whole-sequence buffering when the sequence or reference frame changes', async () => {
        sessionStorage.setItem('lightlyStudio_pointCloudBufferEntireSequence', 'true');
        let playback: ReturnType<typeof useWorkspacePlayback> | undefined;
        const view = render(Harness, {
            workspace: createWorkspace(100),
            options: defaultOptions,
            onReady: (value) => (playback = value)
        });
        flushSync();
        playback?.handleSelectTick(110);
        await view.rerender({
            workspace: createWorkspace(5, 20),
            options: { ...defaultOptions, sequenceId: 'shorter' }
        });
        expect(capture.params?.getRanges()).toEqual([
            { startIndex: 5, endIndex: 19 },
            { startIndex: 0, endIndex: 4 }
        ]);

        await view.rerender({ workspace: { ...createWorkspace(10, 20), referenceFrameId: 'map' } });

        expect(capture.params?.getRanges()).toEqual([
            { startIndex: 10, endIndex: 19 },
            { startIndex: 0, endIndex: 9 }
        ]);
    });
});
