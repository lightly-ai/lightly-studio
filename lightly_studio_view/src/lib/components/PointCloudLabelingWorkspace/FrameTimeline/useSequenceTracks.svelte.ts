import { getTracksOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';

/** Load read-only track membership for the active MCAP sequence. */
export function useSequenceTracks(getIds: () => { datasetId: string; sequenceId: string }) {
    return createQuery(() => {
        const { datasetId, sequenceId } = getIds();
        return {
            ...getTracksOptions({ path: { dataset_id: datasetId, sequence_id: sequenceId } }),
            enabled: Boolean(datasetId && sequenceId)
        };
    });
}
