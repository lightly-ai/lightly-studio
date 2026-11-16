import { getSummaryOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { McapSequenceSummary } from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, useQueryClient, type CreateQueryResult } from '@tanstack/svelte-query';

export const useMcapSequenceSummary = ({
    getDatasetId,
    getSequenceId,
    getEnabled = () => true
}: {
    getDatasetId: () => string;
    getSequenceId: () => string;
    getEnabled?: () => boolean;
}): { summary: CreateQueryResult<McapSequenceSummary, Error>; refetch: () => void } => {
    const client = useQueryClient();
    const summary = createQuery(() => ({
        ...getSummaryOptions({
            path: { dataset_id: getDatasetId(), sequence_id: getSequenceId() }
        }),
        enabled: getEnabled()
    }));
    const refetch = () => {
        client.invalidateQueries({
            queryKey: getSummaryOptions({
                path: { dataset_id: getDatasetId(), sequence_id: getSequenceId() }
            }).queryKey
        });
    };

    return { summary, refetch };
};
