import { getTicksOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { TickListView } from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, useQueryClient, type CreateQueryResult } from '@tanstack/svelte-query';

interface UseMcapSequenceTicksParams {
    getDatasetId: () => string;
    getSequenceId: () => string;
}

interface UseMcapSequenceTicksResult {
    ticks: CreateQueryResult<TickListView, Error>;
    refetch: () => void;
}

/** Loads every indexed tick for an MCAP sequence. */
export function useMcapSequenceTicks({
    getDatasetId,
    getSequenceId
}: UseMcapSequenceTicksParams): UseMcapSequenceTicksResult {
    const client = useQueryClient();
    const getOptions = () =>
        getTicksOptions({
            path: { dataset_id: getDatasetId(), sequence_id: getSequenceId() }
        });
    const ticks = createQuery(() => ({
        ...getOptions(),
        enabled: Boolean(getDatasetId() && getSequenceId())
    }));
    const refetch = () => void client.invalidateQueries({ queryKey: getOptions().queryKey });

    return { ticks, refetch };
}
