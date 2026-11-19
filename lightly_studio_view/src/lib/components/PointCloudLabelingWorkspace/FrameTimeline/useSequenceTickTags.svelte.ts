import { getTickTagsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';

/** Loads the frame tags of the active sequence, grouped by tag, while `enabled` is set. */
export function useSequenceTickTags(
    getParams: () => { datasetId: string; sequenceId: string; enabled: boolean }
) {
    const query = createQuery(() => {
        const { datasetId, sequenceId, enabled } = getParams();
        return {
            ...getTickTagsOptions({
                path: { dataset_id: datasetId, sequence_id: sequenceId }
            }),
            enabled: enabled && Boolean(datasetId) && Boolean(sequenceId)
        };
    });
    return { query };
}
