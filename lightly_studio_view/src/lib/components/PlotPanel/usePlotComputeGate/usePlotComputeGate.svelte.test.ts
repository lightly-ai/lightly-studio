import { flushSync } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
    COMPUTED,
    NOT_COMPUTED_LARGE,
    NOT_COMPUTED_SMALL,
    createCompute,
    createStatusQuery,
    disposeMountedGates,
    mountGate,
    type StatusQueryStub
} from './usePlotComputeGate.testFixtures.svelte';
import { resetComputeTracking } from './usePlotComputeGate.svelte';

const mocks = vi.hoisted(() => ({
    statusQueries: {} as Record<string, StatusQueryStub>
}));

vi.mock('$lib/hooks/useEmbeddingPlotStatus/useEmbeddingPlotStatus', () => ({
    useEmbeddingPlotStatus: (getCollectionId: () => string) => {
        return mocks.statusQueries[getCollectionId()];
    },
    useRefetchEmbeddingPlotStatus: () => (collectionId: string) =>
        mocks.statusQueries[collectionId].refetch()
}));

describe('usePlotComputeGate', () => {
    beforeEach(() => {
        mocks.statusQueries = {};
    });

    afterEach(() => {
        disposeMountedGates();
        resetComputeTracking();
        vi.useRealTimers();
    });

    it('shows the prompt above the threshold and computing after startCompute', () => {
        mocks.statusQueries['prompt-a'] = createStatusQuery(NOT_COMPUTED_LARGE);
        const { gate } = mountGate({ collectionId: 'prompt-a' });

        expect(gate.view).toBe('prompt');
        expect(gate.isPlotRequestEnabled).toBe(false);
        expect(gate.embeddingCount).toBe(300_000);
        expect(gate.startedAt).toBeNull();

        gate.startCompute();
        flushSync();

        expect(gate.view).toBe('computing');
        expect(gate.isPlotRequestEnabled).toBe(true);
        expect(gate.startedAt).toEqual(expect.any(Number));
    });

    it('keeps the start time when the panel remounts', () => {
        vi.useFakeTimers({ now: 1_000_000 });
        mocks.statusQueries['remount'] = createStatusQuery(NOT_COMPUTED_LARGE);
        const first = mountGate({ collectionId: 'remount' });
        first.gate.startCompute();
        flushSync();
        first.dispose();

        vi.setSystemTime(1_060_000);
        const { gate } = mountGate({ collectionId: 'remount' });

        expect(gate.view).toBe('computing');
        expect(gate.startedAt).toBe(1_000_000);
    });

    // The server answers no request while PaCMAP runs, so the status refetch waits for the compute.
    it('shows computing on remount while the status refetch waits for the compute', () => {
        vi.useFakeTimers({ now: 1_000_000 });
        const query = createStatusQuery(NOT_COMPUTED_LARGE);
        mocks.statusQueries['waiting'] = query;
        const first = mountGate({ collectionId: 'waiting' });
        first.gate.startCompute();
        flushSync();
        first.dispose();

        query.isFetchedAfterMount = false;
        const { gate } = mountGate({ collectionId: 'waiting' });

        expect(gate.view).toBe('computing');
        expect(gate.isPlotRequestEnabled).toBe(true);
        expect(gate.startedAt).toBe(1_000_000);
    });

    it('does not share a started compute across collections', () => {
        mocks.statusQueries['share-a'] = createStatusQuery(NOT_COMPUTED_LARGE);
        mocks.statusQueries['share-b'] = createStatusQuery(NOT_COMPUTED_LARGE);
        const a = mountGate({ collectionId: 'share-a' });
        a.gate.startCompute();
        flushSync();

        const { gate } = mountGate({ collectionId: 'share-b' });

        expect(a.gate.view).toBe('computing');
        expect(gate.view).toBe('prompt');
        expect(gate.isPlotRequestEnabled).toBe(false);
    });

    it('starts the timer when a compute below the threshold starts', () => {
        vi.useFakeTimers({ now: 2_000_000 });
        mocks.statusQueries['small'] = createStatusQuery(NOT_COMPUTED_SMALL);
        const { gate } = mountGate({ collectionId: 'small' });

        expect(gate.view).toBe('computing');
        expect(gate.startedAt).toBeNull();

        gate.trackCompute(createCompute().promise);
        flushSync();

        expect(gate.startedAt).toBe(2_000_000);
    });

    it('refetches the status and ends the compute once it succeeds', async () => {
        const query = createStatusQuery(NOT_COMPUTED_LARGE);
        query.refetch = vi.fn(async () => {
            query.data = COMPUTED;
        });
        mocks.statusQueries['success'] = query;
        const { gate } = mountGate({ collectionId: 'success' });
        const compute = createCompute();
        gate.startCompute();
        gate.trackCompute(compute.promise);

        compute.succeed();

        await vi.waitFor(() => expect(gate.startedAt).toBeNull());
        flushSync();
        expect(gate.view).toBe('plot');
    });

    it('asks again above the threshold as soon as a compute fails', async () => {
        const query = createStatusQuery(NOT_COMPUTED_LARGE);
        query.refetch = vi.fn(() => new Promise(() => {}));
        mocks.statusQueries['failed'] = query;
        const { gate } = mountGate({ collectionId: 'failed' });
        const compute = createCompute();
        gate.startCompute();
        gate.trackCompute(compute.promise);

        compute.fail();

        await vi.waitFor(() => expect(gate.startedAt).toBeNull());
        flushSync();
        expect(gate.view).toBe('prompt');
    });

    it('ends a compute that finishes while the panel is closed', async () => {
        const query = createStatusQuery(NOT_COMPUTED_LARGE);
        mocks.statusQueries['closed'] = query;
        const first = mountGate({ collectionId: 'closed' });
        const compute = createCompute();
        first.gate.startCompute();
        first.gate.trackCompute(compute.promise);
        first.dispose();

        compute.succeed();
        await settlePromises();
        const { gate } = mountGate({ collectionId: 'closed' });

        await vi.waitFor(() => expect(gate.startedAt).toBeNull());
        flushSync();
        expect(gate.view).toBe('prompt');
    });

    it('keeps the start until every compute of the collection ends', async () => {
        mocks.statusQueries['two'] = createStatusQuery(NOT_COMPUTED_LARGE);
        const { gate } = mountGate({ collectionId: 'two' });
        const first = createCompute();
        const second = createCompute();
        gate.startCompute();
        gate.trackCompute(first.promise);
        gate.trackCompute(second.promise);

        first.succeed();
        await settlePromises();
        flushSync();
        expect(gate.view).toBe('computing');

        second.succeed();
        await vi.waitFor(() => expect(gate.startedAt).toBeNull());
    });

    it('keeps the start while a compute runs, even if a fresh status says computed', () => {
        const query = createStatusQuery(NOT_COMPUTED_SMALL);
        mocks.statusQueries['still-running'] = query;
        const { gate } = mountGate({ collectionId: 'still-running' });
        gate.trackCompute(createCompute().promise);

        query.data = COMPUTED;
        flushSync();

        expect(gate.startedAt).toEqual(expect.any(Number));
    });

    it('refetches the status of the collection whose compute ended', async () => {
        mocks.statusQueries['switch-a'] = createStatusQuery(NOT_COMPUTED_SMALL);
        mocks.statusQueries['switch-b'] = createStatusQuery(NOT_COMPUTED_SMALL);
        let collectionId = $state('switch-a');
        const { gate } = mountGate({ collectionId: () => collectionId });
        const compute = createCompute();
        gate.trackCompute(compute.promise);

        collectionId = 'switch-b';
        flushSync();
        compute.succeed();

        await vi.waitFor(() =>
            expect(mocks.statusQueries['switch-a'].refetch).toHaveBeenCalledOnce()
        );
        expect(mocks.statusQueries['switch-b'].refetch).not.toHaveBeenCalled();
    });

    it('does not restart the timer when the status stays dirty after a compute', async () => {
        mocks.statusQueries['dirty-again'] = createStatusQuery(NOT_COMPUTED_SMALL);
        const { gate } = mountGate({ collectionId: 'dirty-again' });
        const compute = createCompute();
        gate.trackCompute(compute.promise);

        compute.succeed();

        await vi.waitFor(() => expect(gate.startedAt).toBeNull());
        flushSync();
        expect(gate.view).toBe('computing');
        expect(gate.startedAt).toBeNull();
    });

    it('shows computing on remount after the status cache expired', () => {
        vi.useFakeTimers({ now: 1_000_000 });
        const query = createStatusQuery(NOT_COMPUTED_LARGE);
        mocks.statusQueries['expired'] = query;
        const first = mountGate({ collectionId: 'expired' });
        first.gate.startCompute();
        flushSync();
        first.dispose();

        query.data = undefined;
        query.isFetchedAfterMount = false;
        const { gate } = mountGate({ collectionId: 'expired' });

        expect(gate.view).toBe('computing');
        expect(gate.isPlotRequestEnabled).toBe(true);
    });

    it('waits for a status fetched after mount before it allows the plot request', () => {
        const query = createStatusQuery(COMPUTED);
        query.isFetchedAfterMount = false;
        mocks.statusQueries['cached'] = query;
        const { gate } = mountGate({ collectionId: 'cached' });

        expect(gate.view).toBe('checking');
        expect(gate.isPlotRequestEnabled).toBe(false);

        query.data = NOT_COMPUTED_LARGE;
        query.isFetchedAfterMount = true;
        flushSync();

        expect(gate.view).toBe('prompt');
        expect(gate.isPlotRequestEnabled).toBe(false);
    });

    it('waits for a new status before a changed plot request', async () => {
        const query = createStatusQuery(COMPUTED);
        let finishRefetch = () => {};
        query.refetch = vi.fn(
            () =>
                new Promise<void>((resolve) => {
                    finishRefetch = () => {
                        query.data = NOT_COMPUTED_LARGE;
                        resolve();
                    };
                })
        );
        mocks.statusQueries['changed'] = query;
        let plotRequestKey = $state('all');
        const { gate } = mountGate({
            collectionId: 'changed',
            plotRequestKey: () => plotRequestKey
        });
        expect(gate.view).toBe('plot');

        plotRequestKey = 'filtered';
        flushSync();

        expect(gate.view).toBe('checking');
        expect(gate.isPlotRequestEnabled).toBe(false);

        finishRefetch();
        await vi.waitFor(() => expect(gate.view).toBe('prompt'));
    });

    it('waits for the latest status when the plot request changes back', async () => {
        const query = createStatusQuery(COMPUTED);
        const finishRefetches: (() => void)[] = [];
        query.refetch = vi.fn(
            () =>
                new Promise<void>((resolve) => {
                    finishRefetches.push(() => {
                        query.data = NOT_COMPUTED_LARGE;
                        resolve();
                    });
                })
        );
        mocks.statusQueries['changed-back'] = query;
        let plotRequestKey = $state('all');
        const { gate } = mountGate({
            collectionId: 'changed-back',
            plotRequestKey: () => plotRequestKey
        });

        plotRequestKey = 'filtered';
        flushSync();
        plotRequestKey = 'all';
        flushSync();

        expect(gate.isPlotRequestEnabled).toBe(false);

        const [finishFilteredRefetch, finishAllRefetch] = finishRefetches;
        finishFilteredRefetch();
        await Promise.resolve();
        expect(gate.view).toBe('checking');

        finishAllRefetch();
        await vi.waitFor(() => expect(gate.view).toBe('prompt'));
    });

    it('ignores a status error from before the mount until the new request finishes', () => {
        const query = createStatusQuery(NOT_COMPUTED_LARGE);
        query.isFetchedAfterMount = false;
        query.isError = true;
        query.error = new Error('old');
        mocks.statusQueries['old-error'] = query;
        const { gate } = mountGate({ collectionId: 'old-error' });

        expect(gate.view).toBe('checking');
        expect(gate.statusError).toBeNull();

        query.isFetchedAfterMount = true;
        flushSync();

        expect(gate.view).toBe('error');
    });

    it('reports the status error and keeps the plot request off', () => {
        const query = createStatusQuery(undefined);
        query.isError = true;
        query.error = new Error('boom');
        mocks.statusQueries['error'] = query;
        const { gate } = mountGate({ collectionId: 'error' });

        expect(gate.view).toBe('error');
        expect(gate.statusError).toBe('boom');
        expect(gate.isPlotRequestEnabled).toBe(false);
    });
});

// Lets the `then` callbacks of a settled compute run.
function settlePromises() {
    return new Promise((resolve) => setTimeout(resolve));
}
