import { flushSync } from 'svelte';
import { vi } from 'vitest';
import type { Embeddings2dStatus } from '$lib/api/lightly_studio_local';
import { usePlotComputeGate } from './usePlotComputeGate.svelte';

export interface StatusQueryStub {
    data: Embeddings2dStatus | undefined;
    isFetchedAfterMount: boolean;
    isError: boolean;
    error: Error | null;
    refetch: () => Promise<unknown>;
}

export const NOT_COMPUTED_LARGE: Embeddings2dStatus = {
    is_computed: false,
    embedding_count: 300_000
};
export const NOT_COMPUTED_SMALL: Embeddings2dStatus = {
    is_computed: false,
    embedding_count: 1_000
};
export const COMPUTED: Embeddings2dStatus = { is_computed: true, embedding_count: 300_000 };

let disposers: (() => void)[] = [];

export function createCompute() {
    let succeed = () => {};
    let fail = () => {};
    const promise = new Promise<void>((resolve, reject) => {
        succeed = () => resolve();
        fail = () => reject(new Error('Server error'));
    });
    return { promise, succeed, fail };
}

export function createStatusQuery(data: Embeddings2dStatus | undefined): StatusQueryStub {
    const query: StatusQueryStub = $state({
        data,
        isFetchedAfterMount: true,
        isError: false,
        error: null,
        refetch: vi.fn(async () => undefined)
    });
    return query;
}

export function mountGate(params: {
    collectionId: string | (() => string);
    isAxesLayout?: () => boolean;
    plotRequestKey?: () => string;
}) {
    const { collectionId } = params;
    let gate!: ReturnType<typeof usePlotComputeGate>;
    const dispose = $effect.root(() => {
        gate = usePlotComputeGate({
            getCollectionId: typeof collectionId === 'string' ? () => collectionId : collectionId,
            getIsAxesLayout: params.isAxesLayout ?? (() => false),
            getPlotRequestKey: params.plotRequestKey ?? (() => 'request')
        });
    });
    disposers.push(dispose);
    flushSync();
    return { gate, dispose };
}

export function disposeMountedGates() {
    for (const dispose of disposers) dispose();
    disposers = [];
}
