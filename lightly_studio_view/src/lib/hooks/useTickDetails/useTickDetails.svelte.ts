import { getTickDetailsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { TickDetailView } from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, type CreateQueryResult } from '@tanstack/svelte-query';

interface UseTickDetailsParams {
    getDatasetId: () => string;
    getSequenceId: () => string;
    getSeqNumber: () => number;
}

interface UseTickDetailsReturn {
    tickDetails: CreateQueryResult<TickDetailView, Error>;
}

export const useTickDetails = ({
    getDatasetId,
    getSequenceId,
    getSeqNumber
}: UseTickDetailsParams): UseTickDetailsReturn => {
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
            enabled: Boolean(datasetId) && Boolean(sequenceId)
        };
    });

    return { tickDetails };
};
