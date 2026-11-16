import { fromStore, writable } from 'svelte/store';
import { untrack } from 'svelte';
import { useEmbeddingPlotStatus } from '$lib/hooks';
import { getPlotComputeView, isPlotRequestEnabled, type PlotComputeView } from '../plotComputeGate';

interface UsePlotComputeGateParams {
    getCollectionId: () => string;
    getIsAxesLayout: () => boolean;
    getPlotUpdatedAt: () => number;
}

interface UsePlotComputeGateReturn {
    readonly view: PlotComputeView;
    readonly isPlotRequestEnabled: boolean;
    readonly embeddingCount: number;
    readonly startedAt: number | null;
    readonly statusError: string | null;
    startCompute(): void;
}

// Module scope, so a compute that runs on keeps its start time when the panel closes and opens.
const computeStartTimes = writable<Record<string, number>>({});

export function usePlotComputeGate(params: UsePlotComputeGateParams): UsePlotComputeGateReturn {
    const { getCollectionId, getIsAxesLayout, getPlotUpdatedAt } = params;
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

    // Below the threshold the compute starts without a click, so the timer starts here.
    $effect(() => {
        if (view === 'computing' && startedAt === null) untrack(startCompute);
    });

    // A finished compute saves the plot, so the status is outdated once per plot load.
    $effect(() => {
        if (getPlotUpdatedAt() === 0) return;
        untrack(() => {
            if (statusQuery.data?.is_computed === false) statusQuery.refetch();
        });
    });

    // The compute ends once a plot load finished after the start and the status refresh after that
    // load returned, even if the plot is dirty again: a kept start would skip the prompt next time.
    $effect(() => {
        if (startedAt === null) return;
        const plotUpdatedAt = getPlotUpdatedAt();
        const isLoadedAfterStart = plotUpdatedAt > startedAt;
        const isStatusAfterLoad = statusQuery.dataUpdatedAt >= plotUpdatedAt;
        const isComputeOver =
            freshStatus?.is_computed === true || (isLoadedAfterStart && isStatusAfterLoad);
        if (isComputeOver) untrack(() => clearComputeStart(getCollectionId()));
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
        startCompute
    };
}

function clearComputeStart(collectionId: string) {
    computeStartTimes.update((times) =>
        Object.fromEntries(Object.entries(times).filter(([id]) => id !== collectionId))
    );
}
