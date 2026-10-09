import {
    getSummaryOptions,
    getTicksOptions
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { useQueryClient } from '@tanstack/svelte-query';
import { prefetchMcapTick } from '$lib/hooks/useMcapTickDetailsPrefetch/prefetchMcapTick';

/** Number of ticks used to seed a sequence opened from the grid. */
export const MCAP_GRID_PREFETCH_TICKS = 10;

/** Prefetches the metadata required to open an MCAP sequence detail view. */
export const useMcapSequencePrefetch = (getDatasetId: () => string) => {
    const client = useQueryClient();
    const prefetchedSequences = new Set<string>();
    const inFlightSequences = new Map<string, Promise<void>>();

    const prefetch = (sequenceId: string): Promise<void> | undefined => {
        const datasetId = getDatasetId();
        if (!datasetId || !sequenceId) return undefined;
        const key = `${datasetId}/${sequenceId}`;
        if (prefetchedSequences.has(key)) return undefined;
        const inFlight = inFlightSequences.get(key);
        if (inFlight) return inFlight;

        const request = prefetchSequence(datasetId, sequenceId)
            .then(() => {
                prefetchedSequences.add(key);
            })
            .catch(() => undefined)
            .finally(() => inFlightSequences.delete(key));
        inFlightSequences.set(key, request);
        return request;
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
            ticks.ticks.slice(0, MCAP_GRID_PREFETCH_TICKS).map((tick) =>
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
