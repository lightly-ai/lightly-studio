import { getSequenceTracksOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';

/** Loads annotation coverage for every tick in the active sequence. */
export function useSequenceTracks(getParams: () => { datasetId: string; sequenceId: string }) {
    const query = createQuery(() => {
        const { datasetId, sequenceId } = getParams();
        return {
            ...getSequenceTracksOptions({
                path: { dataset_id: datasetId, sequence_id: sequenceId }
            }),
            enabled: Boolean(datasetId) && Boolean(sequenceId)
        };
    });
    return { query };
}
