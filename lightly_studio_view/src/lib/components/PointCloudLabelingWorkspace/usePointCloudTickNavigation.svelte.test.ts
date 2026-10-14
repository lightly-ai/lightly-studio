import { render } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { PointCloudWorkspaceContext } from './provider/types';
import Harness from './UsePointCloudTickNavigationHarness.svelte';

interface QueryState {
    isFetching: boolean;
    isPlaceholderData: boolean;
    isEnabled?: boolean;
}

function createWorkspace(
    overrides: {
        tickDetails?: Partial<QueryState>;
        cloudPointFrame?: Partial<QueryState>;
    } = {}
) {
    return {
        isPlaying: true,
        playbackIntervalMs: 100,
        ticks: [{ seq_number: 0 }, { seq_number: 1 }],
        currentTick: 0,
        tickDetails: {
            isFetching: false,
            isPlaceholderData: false,
            ...overrides.tickDetails
        },
        cloudPointFrame: {
            isFetching: false,
            isPlaceholderData: false,
            isEnabled: true,
            ...overrides.cloudPointFrame
        },
        goToFrame: vi.fn(),
        goToPreviousFrame: vi.fn(),
        goToNextFrame: vi.fn(),
        togglePlayback: vi.fn()
    } as unknown as PointCloudWorkspaceContext;
}

function renderHook(workspace: PointCloudWorkspaceContext) {
    let result: unknown;
    render(Harness, {
        workspace,
        tickNumber: 1,
        onReady: (value) => (result = value)
    });
    flushSync();
    return result;
}

describe('usePointCloudTickNavigation', () => {
    afterEach(() => {
        vi.useRealTimers();
    });

    it.each([
        { name: 'tick details fetching', tickDetails: { isFetching: true } },
        { name: 'cloud frame fetching', cloudPointFrame: { isFetching: true } },
        { name: 'tick details placeholder', tickDetails: { isPlaceholderData: true } },
        { name: 'enabled cloud frame placeholder', cloudPointFrame: { isPlaceholderData: true } }
    ])('waits for $name before advancing playback', ({ tickDetails, cloudPointFrame }) => {
        vi.useFakeTimers();
        const workspace = createWorkspace({ tickDetails, cloudPointFrame });

        renderHook(workspace);
        vi.advanceTimersByTime(workspace.playbackIntervalMs);

        expect(workspace.goToNextFrame).not.toHaveBeenCalled();
    });

    it('continues playback when the cloud query is disabled', () => {
        vi.useFakeTimers();
        const workspace = createWorkspace({
            cloudPointFrame: { isPlaceholderData: true, isEnabled: false }
        });

        renderHook(workspace);
        vi.advanceTimersByTime(workspace.playbackIntervalMs);

        expect(workspace.goToNextFrame).toHaveBeenCalledOnce();
    });
});
