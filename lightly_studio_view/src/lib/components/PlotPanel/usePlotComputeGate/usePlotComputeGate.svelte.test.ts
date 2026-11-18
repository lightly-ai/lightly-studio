import { flushSync } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Embeddings2dStatus } from '$lib/api/lightly_studio_local';
import { usePlotComputeGate } from './usePlotComputeGate.svelte';

interface StatusQueryStub {
    data: Embeddings2dStatus | undefined;
    isFetchedAfterMount: boolean;
    isError: boolean;
    error: Error | null;
    refetch: () => Promise<unknown>;
}

const mocks = vi.hoisted(() => ({
    statusQueries: {} as Record<string, StatusQueryStub>
}));

vi.mock('$lib/hooks/useEmbeddingPlotStatus/useEmbeddingPlotStatus', () => ({
    useEmbeddingPlotStatus: (getCollectionId: () => string) => {
        return mocks.statusQueries[getCollectionId()];
    }
}));

const NOT_COMPUTED_LARGE: Embeddings2dStatus = { is_computed: false, embedding_count: 300_000 };
const NOT_COMPUTED_SMALL: Embeddings2dStatus = { is_computed: false, embedding_count: 1_000 };
const COMPUTED: Embeddings2dStatus = { is_computed: true, embedding_count: 300_000 };

let disposers: (() => void)[] = [];

function createCompute() {
    let succeed = () => {};
    let fail = () => {};
    const promise = new Promise<void>((resolve, reject) => {
        succeed = () => resolve();
        fail = () => reject(new Error('Server error'));
    });
    return { promise, succeed, fail };
}

function createStatusQuery(data: Embeddings2dStatus | undefined): StatusQueryStub {
    const query: StatusQueryStub = $state({
        data,
        isFetchedAfterMount: true,
        isError: false,
        error: null,
        refetch: vi.fn(async () => undefined)
    });
    return query;
}

function mountGate(params: { collectionId: string; isAxesLayout?: () => boolean }) {
    let gate!: ReturnType<typeof usePlotComputeGate>;
    const dispose = $effect.root(() => {
        gate = usePlotComputeGate({
            getCollectionId: () => params.collectionId,
            getIsAxesLayout: params.isAxesLayout ?? (() => false)
        });
    });
    disposers.push(dispose);
    flushSync();
    return { gate, dispose };
}

describe('usePlotComputeGate', () => {
    beforeEach(() => {
        mocks.statusQueries = {};
    });

    afterEach(() => {
        for (const dispose of disposers) dispose();
        disposers = [];
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
        expect(query.refetch).toHaveBeenCalledOnce();
        expect(gate.view).toBe('plot');
    });

    it('asks again above the threshold after a compute fails', async () => {
        mocks.statusQueries['failed'] = createStatusQuery(NOT_COMPUTED_LARGE);
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
        await vi.waitFor(() => expect(query.refetch).toHaveBeenCalledOnce());
        const { gate } = mountGate({ collectionId: 'closed' });

        await vi.waitFor(() => expect(gate.startedAt).toBeNull());
        flushSync();
        expect(gate.view).toBe('prompt');
    });

    it('ends a retried compute once', async () => {
        const query = createStatusQuery(NOT_COMPUTED_SMALL);
        mocks.statusQueries['retried'] = query;
        const { gate } = mountGate({ collectionId: 'retried' });
        const compute = createCompute();
        gate.trackCompute(compute.promise);
        gate.trackCompute(compute.promise);

        compute.succeed();

        await vi.waitFor(() => expect(gate.startedAt).toBeNull());
        expect(query.refetch).toHaveBeenCalledOnce();
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
