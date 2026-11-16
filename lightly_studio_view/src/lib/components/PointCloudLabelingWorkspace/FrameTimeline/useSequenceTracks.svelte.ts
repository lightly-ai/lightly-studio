import { getSequenceTracksOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';

/**
 * Loads annotation coverage for every tick in the active sequence.
 *
 * Pass the frame the scene is shown in, so ticks whose cuboids the scene cannot show in that
 * frame are left out, as in the tick details.
 */
export function useSequenceTracks(
    getParams: () => { datasetId: string; sequenceId: string; displayFrameId?: string }
) {
    const query = createQuery(() => {
        const { datasetId, sequenceId, displayFrameId } = getParams();
        return {
            ...getSequenceTracksOptions({
                path: { dataset_id: datasetId, sequence_id: sequenceId },
                query: displayFrameId ? { target_frame_id: displayFrameId } : undefined
            }),
            enabled: Boolean(datasetId) && Boolean(sequenceId)
        };
    });
    return { query };
}
