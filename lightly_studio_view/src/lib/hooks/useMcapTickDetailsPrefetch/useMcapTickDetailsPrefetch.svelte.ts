import { useQueryClient } from '@tanstack/svelte-query';
import type { TickView } from '$lib/api/lightly_studio_local/types.gen';
import { prefetchMcapTick } from './prefetchMcapTick';

/** Number of future tick details kept warm during playback. */
export const MCAP_PLAYBACK_PREFETCH_TICKS = 2;

interface McapTickDetailsPrefetchParams {
    getDatasetId: () => string;
    getSequenceId: () => string;
    getDisplayFrameId: () => string | undefined;
    getTicks: () => TickView[];
    getCurrentTick: () => number;
}

/** Prefetches selected future ticks using the same keys as the visible workspace query. */
export const useMcapTickDetailsPrefetch = ({
    getDatasetId,
    getSequenceId,
    getDisplayFrameId,
    getTicks,
    getCurrentTick
}: McapTickDetailsPrefetchParams) => {
    const client = useQueryClient();

    const prefetch = (sequenceNumbers: number[]) => {
        const datasetId = getDatasetId();
        const sequenceId = getSequenceId();
        if (!datasetId || !sequenceId) return;

        for (const seqNumber of sequenceNumbers) {
            void prefetchMcapTick(client, {
                datasetId,
                sequenceId,
                seqNumber,
                displayFrameId: getDisplayFrameId()
            });
        }
    };

    $effect(() => {
        const ticks = getTicks();
        const currentIndex = ticks.findIndex((tick) => tick.seq_number === getCurrentTick());
        if (currentIndex < 0) return;

        prefetch(
            ticks
                .slice(currentIndex + 1, currentIndex + 1 + MCAP_PLAYBACK_PREFETCH_TICKS)
                .map((tick) => tick.seq_number)
        );
    });

    return { prefetch };
};
