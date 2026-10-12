import { useQueryClient } from '@tanstack/svelte-query';
import type { TickView } from '$lib/api/lightly_studio_local/types.gen';
import { prefetchMcapTick } from './prefetchMcapTick';

interface McapTickDetailsPrefetchParams {
    getDatasetId: () => string;
    getSequenceId: () => string;
    getDisplayFrameId: () => string | undefined;
    getTicks: () => TickView[];
    getCurrentTick: () => number;
}

/** Prefetches every tick after the active tick using the same keys as visible workspace queries. */
export const useMcapTickDetailsPrefetch = ({
    getDatasetId,
    getSequenceId,
    getDisplayFrameId,
    getTicks,
    getCurrentTick
}: McapTickDetailsPrefetchParams) => {
    const client = useQueryClient();
    let bufferedTickNumbers = $state<number[]>([]);
    const inFlight = new Map<number, Promise<void>>();
    let bufferKey = '';

    const resetForContext = () => {
        const datasetId = getDatasetId();
        const sequenceId = getSequenceId();
        const displayFrameId = getDisplayFrameId() ?? '';
        const nextKey = `${datasetId}/${sequenceId}/${displayFrameId}`;
        if (nextKey === bufferKey) return;
        bufferKey = nextKey;
        bufferedTickNumbers = [];
        inFlight.clear();
    };

    const prefetchTick = (seqNumber: number) => {
        if (bufferedTickNumbers.includes(seqNumber) || inFlight.has(seqNumber)) return;

        const datasetId = getDatasetId();
        const sequenceId = getSequenceId();
        if (!datasetId || !sequenceId) return;
        const requestKey = bufferKey;

        const request = prefetchMcapTick(client, {
            datasetId,
            sequenceId,
            seqNumber,
            displayFrameId: getDisplayFrameId()
        })
            .then(() => {
                if (bufferKey !== requestKey) return;
                if (!bufferedTickNumbers.includes(seqNumber)) {
                    bufferedTickNumbers = [...bufferedTickNumbers, seqNumber].sort(
                        (left, right) => left - right
                    );
                }
            })
            .catch(() => undefined)
            .finally(() => {
                if (bufferKey === requestKey) inFlight.delete(seqNumber);
            });
        inFlight.set(seqNumber, request);
    };

    $effect(() => {
        resetForContext();
        const ticks = getTicks();
        const currentTick = getCurrentTick();
        const currentIndex = ticks.findIndex((tick) => tick.seq_number === currentTick);
        if (currentIndex < 0) return;

        for (const tick of ticks.slice(currentIndex + 1)) {
            prefetchTick(tick.seq_number);
        }
    });

    return {
        get bufferedTickNumbers() {
            return bufferedTickNumbers;
        }
    };
};
