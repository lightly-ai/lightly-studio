import { render } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { PointCloudWorkspaceContext } from './provider/types';
import Harness from './UsePointCloudTickNavigationHarness.svelte';

interface QueryState {
    data: unknown;
    isPending: boolean;
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
            data: {},
            isPending: false,
            isFetching: false,
            isPlaceholderData: false,
            ...overrides.tickDetails
        },
        cloudPointFrame: {
            data: {},
            isPending: false,
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

function renderHook(
    workspace: PointCloudWorkspaceContext,
    isTickBuffered: (index: number) => boolean = () => true
) {
    let result: unknown;
    render(Harness, {
        workspace,
        tickNumber: 1,
        isTickBuffered,
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
        { name: 'tick details missing', tickDetails: { data: undefined, isPending: true } },
        { name: 'cloud frame missing', cloudPointFrame: { data: undefined, isPending: true } },
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

    it('advances cached frames while their queries refresh in the background', () => {
        vi.useFakeTimers();
        const workspace = createWorkspace({
            tickDetails: { isFetching: true },
            cloudPointFrame: { isFetching: true }
        });
        renderHook(workspace);
        vi.advanceTimersByTime(100);
        expect(workspace.goToNextFrame).toHaveBeenCalledOnce();
    });

    it('does not restart the playback interval when other buffered ticks finish', async () => {
        vi.useFakeTimers();
        const workspace = createWorkspace();
        const props = {
            workspace,
            tickNumber: 1,
            isTickBuffered: (index: number) => index === 1,
            onReady: () => undefined
        };
        const view = render(Harness, props);
        flushSync();
        await vi.advanceTimersByTimeAsync(60);
        await view.rerender({ isTickBuffered: (index: number) => index <= 2 });
        flushSync();
        await vi.advanceTimersByTimeAsync(40);
        expect(workspace.goToNextFrame).toHaveBeenCalledOnce();
    });

    it('waits when the next tick is not buffered', () => {
        vi.useFakeTimers();
        const workspace = createWorkspace();

        renderHook(workspace, () => false);
        vi.advanceTimersByTime(workspace.playbackIntervalMs);

        expect(workspace.goToNextFrame).not.toHaveBeenCalled();
    });

    it('cancels a pending step on pause and applies a changed playback speed', async () => {
        vi.useFakeTimers();
        const workspace = createWorkspace();
        const view = render(Harness, {
            workspace,
            tickNumber: 1,
            onReady: () => undefined
        });
        flushSync();
        await vi.advanceTimersByTimeAsync(60);
        await view.rerender({ workspace: { ...workspace, isPlaying: false } });
        await vi.advanceTimersByTimeAsync(100);
        expect(workspace.goToNextFrame).not.toHaveBeenCalled();

        await view.rerender({ workspace: { ...workspace, playbackIntervalMs: 200 } });
        await vi.advanceTimersByTimeAsync(100);
        expect(workspace.goToNextFrame).not.toHaveBeenCalled();
        await vi.advanceTimersByTimeAsync(100);
        expect(workspace.goToNextFrame).toHaveBeenCalledOnce();
    });

    it('restarts playback timing from a newly selected frame', async () => {
        vi.useFakeTimers();
        const workspace = {
            ...createWorkspace(),
            ticks: [{ seq_number: 0 }, { seq_number: 1 }, { seq_number: 2 }]
        } as PointCloudWorkspaceContext;
        let goToFrame: (seqNumber: number) => void = () => undefined;
        const view = render(Harness, {
            workspace,
            tickNumber: 1,
            onReady: (navigation) => {
                goToFrame = navigation.goToFrame;
            }
        });
        flushSync();

        await vi.advanceTimersByTimeAsync(60);
        goToFrame(1);
        await view.rerender({ workspace: { ...workspace, currentTick: 1 } });
        flushSync();
        await vi.advanceTimersByTimeAsync(40);
        expect(workspace.goToNextFrame).not.toHaveBeenCalled();

        await vi.advanceTimersByTimeAsync(60);
        expect(workspace.goToNextFrame).toHaveBeenCalledOnce();
    });

    it('resumes when the next tick finishes buffering and clears the timer on unmount', async () => {
        vi.useFakeTimers();
        const workspace = createWorkspace();
        const view = render(Harness, {
            workspace,
            tickNumber: 1,
            isTickBuffered: () => false,
            onReady: () => undefined
        });
        flushSync();
        await vi.advanceTimersByTimeAsync(200);
        expect(workspace.goToNextFrame).not.toHaveBeenCalled();

        await view.rerender({ isTickBuffered: () => true });
        await vi.advanceTimersByTimeAsync(100);
        expect(workspace.goToNextFrame).toHaveBeenCalledOnce();

        await view.rerender({ isTickBuffered: () => false });
        await view.rerender({ isTickBuffered: () => true });
        view.unmount();
        await vi.advanceTimersByTimeAsync(100);
        expect(workspace.goToNextFrame).toHaveBeenCalledOnce();
    });

    it('does not wait for a buffer when no buffering check is provided', () => {
        vi.useFakeTimers();
        const workspace = createWorkspace();

        renderHook(workspace);
        vi.advanceTimersByTime(workspace.playbackIntervalMs);

        expect(workspace.goToNextFrame).toHaveBeenCalledOnce();
    });
});
