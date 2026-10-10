import {
    getSummaryOptions,
    getTicksOptions
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { useQueryClient } from '@tanstack/svelte-query';
import { MCAP_PLAYBACK_PREFETCH_TICKS } from '$lib/hooks/useMcapTickDetailsPrefetch';
import { prefetchMcapTick } from '$lib/hooks/useMcapTickDetailsPrefetch/prefetchMcapTick';

/** Prefetches the metadata required to open an MCAP sequence detail view. */
export const useMcapSequencePrefetch = (getDatasetId: () => string) => {
    const client = useQueryClient();

    const prefetch = (sequenceId: string) => {
        const datasetId = getDatasetId();
        if (!datasetId || !sequenceId) return;

        void prefetchSequence(datasetId, sequenceId);
    };

    const prefetchSequence = async (datasetId: string, sequenceId: string) => {
        const [ticks] = await Promise.all([
            client.ensureQueryData(
                getTicksOptions({ path: { dataset_id: datasetId, sequence_id: sequenceId } })
            ),
            client.ensureQueryData(
                getSummaryOptions({ path: { dataset_id: datasetId, sequence_id: sequenceId } })
            )
        ]);
        await Promise.all(
            ticks.ticks.slice(0, MCAP_PLAYBACK_PREFETCH_TICKS).map((tick) =>
                prefetchMcapTick(client, {
                    datasetId,
                    sequenceId,
                    seqNumber: tick.seq_number
                })
            )
        );
    };

    const cancel = (sequenceId: string) => {
        const datasetId = getDatasetId();
        if (!datasetId || !sequenceId) return;

        const summaryOptions = getSummaryOptions({
            path: { dataset_id: datasetId, sequence_id: sequenceId }
        });
        const ticksOptions = getTicksOptions({
            path: { dataset_id: datasetId, sequence_id: sequenceId }
        });
        void client.cancelQueries({ queryKey: summaryOptions.queryKey, exact: true });
        void client.cancelQueries({ queryKey: ticksOptions.queryKey, exact: true });
    };

    return { cancel, prefetch };
};
