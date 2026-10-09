import { useQueryClient } from '@tanstack/svelte-query';
import type { TickView } from '$lib/api/lightly_studio_local/types.gen';
import { prefetchMcapTick } from './prefetchMcapTick';

/** Target amount of playback time kept buffered ahead of the active tick. */
export const MCAP_PLAYBACK_BUFFER_SECONDS = 5;

interface McapTickDetailsPrefetchParams {
    getDatasetId: () => string;
    getSequenceId: () => string;
    getDisplayFrameId: () => string | undefined;
    getTicks: () => TickView[];
    getCurrentTick: () => number;
    getPlaybackIntervalMs: () => number;
}

/** Keeps a time-based playback buffer warm using the same keys as visible workspace queries. */
export const useMcapTickDetailsPrefetch = ({
    getDatasetId,
    getSequenceId,
    getDisplayFrameId,
    getTicks,
    getCurrentTick,
    getPlaybackIntervalMs
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

        const currentTimestamp = ticks[currentIndex]?.timestamp_ns;
        const targetTimestamp =
            currentTimestamp === null || currentTimestamp === undefined
                ? undefined
                : currentTimestamp + MCAP_PLAYBACK_BUFFER_SECONDS * 1_000_000_000;
        const fallbackCount = Math.max(
            1,
            Math.ceil((MCAP_PLAYBACK_BUFFER_SECONDS * 1000) / Math.max(1, getPlaybackIntervalMs()))
        );
        const targetIndex = ticks.findIndex((tick, index) => {
            if (index <= currentIndex) return false;
            if (targetTimestamp === undefined || tick.timestamp_ns === null) {
                return index >= currentIndex + fallbackCount;
            }
            return tick.timestamp_ns >= targetTimestamp;
        });
        const endIndex = targetIndex < 0 ? ticks.length : targetIndex + 1;
        for (const tick of ticks.slice(currentIndex + 1, endIndex)) {
            prefetchTick(tick.seq_number);
        }
    });

    return {
        get bufferedTickNumbers() {
            return bufferedTickNumbers;
        }
    };
};
