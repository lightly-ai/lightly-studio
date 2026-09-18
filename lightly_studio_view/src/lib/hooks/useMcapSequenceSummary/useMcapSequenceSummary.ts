import { getSummaryOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { McapSequenceSummary } from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, useQueryClient, type CreateQueryResult } from '@tanstack/svelte-query';

export const useMcapSequenceSummary = ({
    getDatasetId,
    getSequenceId
}: {
    getDatasetId: () => string;
    getSequenceId: () => string;
}): { summary: CreateQueryResult<McapSequenceSummary, Error>; refetch: () => void } => {
    const client = useQueryClient();
    const summary = createQuery(() =>
        getSummaryOptions({
            path: { dataset_id: getDatasetId(), sequence_id: getSequenceId() }
        })
    );
    const refetch = () => {
        client.invalidateQueries({
            queryKey: getSummaryOptions({
                path: { dataset_id: getDatasetId(), sequence_id: getSequenceId() }
            }).queryKey
        });
    };

    return { summary, refetch };
};
