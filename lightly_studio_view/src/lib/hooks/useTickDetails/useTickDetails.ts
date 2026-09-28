import { getTickDetailsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { TickDetailView } from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, keepPreviousData, type CreateQueryResult } from '@tanstack/svelte-query';

export const useTickDetails = ({
    getDatasetId,
    getSequenceId,
    getSeqNumber
}: {
    getDatasetId: () => string;
    getSequenceId: () => string;
    getSeqNumber: () => number;
}): { tickDetails: CreateQueryResult<TickDetailView, Error> } => {
    const tickDetails = createQuery(() => {
        const datasetId = getDatasetId();
        const sequenceId = getSequenceId();
        return {
            ...getTickDetailsOptions({
                path: {
                    dataset_id: datasetId,
                    sequence_id: sequenceId,
                    seq_number: getSeqNumber()
                }
            }),
            enabled: Boolean(datasetId) && Boolean(sequenceId),
            // Keep the previous tick while the next one loads, so stepping does not flash a spinner.
            placeholderData: keepPreviousData
        };
    });

    return { tickDetails };
};
