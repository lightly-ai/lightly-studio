import { fromStore, writable } from 'svelte/store';
import { untrack } from 'svelte';
import { useEmbeddingPlotStatus } from '$lib/hooks';
import { getPlotComputeView, isPlotRequestEnabled, type PlotComputeView } from '../plotComputeGate';

interface UsePlotComputeGateParams {
    getCollectionId: () => string;
    getIsAxesLayout: () => boolean;
}

interface UsePlotComputeGateReturn {
    readonly view: PlotComputeView;
    readonly isPlotRequestEnabled: boolean;
    readonly embeddingCount: number;
    readonly startedAt: number | null;
    readonly statusError: string | null;
    startCompute(): void;
    trackCompute(compute: Promise<unknown>): void;
}

// Module scope, so a compute that runs on keeps its start time when the panel closes and opens.
const computeStartTimes = writable<Record<string, number>>({});
// Each retry of a compute gives the same promise again.
const trackedComputes = new WeakSet<Promise<unknown>>();

export function usePlotComputeGate(params: UsePlotComputeGateParams): UsePlotComputeGateReturn {
    const { getCollectionId, getIsAxesLayout } = params;
    const statusQuery = useEmbeddingPlotStatus(getCollectionId);
    const startTimes = fromStore(computeStartTimes);

    const startedAt = $derived(startTimes.current[getCollectionId()] ?? null);
    // A cached status can be outdated after embeddings were added, so only a fresh one decides.
    // A compute started in this tab is the exception: the server answers no request while it runs.
    const isStatusTrusted = $derived(statusQuery.isFetchedAfterMount || startedAt !== null);
    const freshStatus = $derived(isStatusTrusted ? statusQuery.data : undefined);
    const view = $derived(
        getPlotComputeView({
            status: freshStatus,
            isStatusError: statusQuery.isError,
            isAxesLayout: getIsAxesLayout(),
            isComputeStarted: startedAt !== null
        })
    );

    function startCompute() {
        const collectionId = getCollectionId();
        computeStartTimes.update((times) =>
            collectionId in times ? times : { ...times, [collectionId]: Date.now() }
        );
    }

    // The compute can outlive the panel, so its promise, not an effect, ends it.
    function trackCompute(compute: Promise<unknown>) {
        startCompute();
        if (trackedComputes.has(compute)) return;
        trackedComputes.add(compute);
        const collectionId = getCollectionId();
        // A failed compute also ends, so the next one asks again above the threshold.
        const endCompute = async () => {
            await statusQuery.refetch();
            clearComputeStart(collectionId);
        };
        void compute.then(endCompute, endCompute);
    }

    $effect(() => {
        if (startedAt === null || freshStatus?.is_computed !== true) return;
        untrack(() => clearComputeStart(getCollectionId()));
    });

    return {
        get view() {
            return view;
        },
        get isPlotRequestEnabled() {
            return isPlotRequestEnabled(view);
        },
        get embeddingCount() {
            return statusQuery.data?.embedding_count ?? 0;
        },
        get startedAt() {
            return startedAt;
        },
        get statusError() {
            if (!statusQuery.isError) return null;
            return statusQuery.error?.message || 'Unknown error';
        },
        startCompute,
        trackCompute
    };
}

function clearComputeStart(collectionId: string) {
    computeStartTimes.update((times) =>
        Object.fromEntries(Object.entries(times).filter(([id]) => id !== collectionId))
    );
}
