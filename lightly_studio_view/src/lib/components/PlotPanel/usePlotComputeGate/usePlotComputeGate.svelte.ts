import { fromStore, writable } from 'svelte/store';
import { untrack } from 'svelte';
import { useEmbeddingPlotStatus, useRefetchEmbeddingPlotStatus } from '$lib/hooks';
import { getPlotComputeView, isPlotRequestEnabled, type PlotComputeView } from '../plotComputeGate';

interface UsePlotComputeGateParams {
    getCollectionId: () => string;
    getIsAxesLayout: () => boolean;
    getPlotRequestKey: () => string;
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
// Two computes of one collection can run at once, for example after a filter change.
const pendingComputes = new Map<string, Set<Promise<unknown>>>();

export function usePlotComputeGate(params: UsePlotComputeGateParams): UsePlotComputeGateReturn {
    const { getCollectionId, getIsAxesLayout, getPlotRequestKey } = params;
    const statusQuery = useEmbeddingPlotStatus(getCollectionId);
    const refetchStatus = useRefetchEmbeddingPlotStatus();
    const startTimes = fromStore(computeStartTimes);

    const startedAt = $derived(startTimes.current[getCollectionId()] ?? null);
    const plotRequestKey = $derived(getPlotRequestKey());
    // Embeddings can change while the panel is open, so a new plot request waits for a new status.
    let checkedPlotRequestKey = $state<string | null>(untrack(getPlotRequestKey));
    // Counts status checks, so a slow check for an older plot request approves nothing.
    let latestStatusCheck = 0;
    // A cached status can be outdated after embeddings were added, so only a fresh one decides.
    // A compute started in this tab is the exception: the server answers no request while it runs.
    const isStatusTrusted = $derived(
        startedAt !== null ||
            (statusQuery.isFetchedAfterMount && checkedPlotRequestKey === plotRequestKey)
    );
    const freshStatus = $derived(isStatusTrusted ? statusQuery.data : undefined);
    // An error from before this mount stays in the cache until the new request finishes.
    const isStatusError = $derived(statusQuery.isError && statusQuery.isFetchedAfterMount);
    const view = $derived(
        getPlotComputeView({
            status: freshStatus,
            isStatusError,
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
        const collectionId = getCollectionId();
        const pending = pendingComputes.get(collectionId) ?? new Set();
        // Each retry of a compute gives the same promise again.
        if (pending.has(compute)) return;
        pending.add(compute);
        pendingComputes.set(collectionId, pending);
        const endCompute = () => {
            pending.delete(compute);
            if (pending.size > 0) return;
            pendingComputes.delete(collectionId);
            clearComputeStart(collectionId);
        };
        // A saved plot ends after the status refresh, so the prompt does not show over it.
        // A failed compute ends at once, so the next one asks again above the threshold.
        void compute.then(
            () => refetchStatus(collectionId).then(endCompute),
            () => {
                endCompute();
                void refetchStatus(collectionId);
            }
        );
    }

    $effect(() => {
        const key = plotRequestKey;
        // The first run has the mounted key, which the status request on mount checks.
        if (key === untrack(() => checkedPlotRequestKey)) return;
        checkedPlotRequestKey = null;
        const statusCheck = ++latestStatusCheck;
        void untrack(() => statusQuery.refetch()).then(() => {
            if (statusCheck === latestStatusCheck) checkedPlotRequestKey = key;
        });
    });

    $effect(() => {
        if (startedAt === null || freshStatus?.is_computed !== true) return;
        untrack(() => {
            const collectionId = getCollectionId();
            if (!pendingComputes.has(collectionId)) clearComputeStart(collectionId);
        });
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
            if (!isStatusError) return null;
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
