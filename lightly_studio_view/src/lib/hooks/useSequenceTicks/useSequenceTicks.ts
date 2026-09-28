import { getTicksOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { TickListView } from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, type CreateQueryResult } from '@tanstack/svelte-query';

/** Loads the ordered ticks of an MCAP sequence, e.g. to step through its frames. */
export const useSequenceTicks = ({
    getDatasetId,
    getSequenceId
}: {
    getDatasetId: () => string;
    getSequenceId: () => string;
}): { sequenceTicks: CreateQueryResult<TickListView, Error> } => {
    const sequenceTicks = createQuery(() => {
        const datasetId = getDatasetId();
        const sequenceId = getSequenceId();
        return {
            ...getTicksOptions({
                path: { dataset_id: datasetId, sequence_id: sequenceId }
            }),
            enabled: Boolean(datasetId) && Boolean(sequenceId)
        };
    });

    return { sequenceTicks };
};
