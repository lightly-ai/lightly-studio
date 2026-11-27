import { createQuery } from '@tanstack/svelte-query';
import { getTickEgoPositionOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { TickEgoPositionView } from '$lib/api/lightly_studio_local/types.gen';
import { keepPositionForSameFrames } from './keepPositionForSameFrames';

interface UseEgoPositionParams {
    datasetId: string;
    sequenceId: string;
    seqNumber: number;
    /** Frame the scene is shown in. */
    referenceFrameId: string;
    /** Frame attached to the ego, e.g. a vehicle or a robot. */
    egoFrameId: string;
    enabled: boolean;
}

/** Loads the position of the ego at one tick, in the frame the scene is shown in. */
export function useEgoPosition(getParams: () => UseEgoPositionParams) {
    const query = createQuery(() => {
        const { datasetId, sequenceId, seqNumber, referenceFrameId, egoFrameId, enabled } =
            getParams();
        return {
            ...getTickEgoPositionOptions({
                path: { dataset_id: datasetId, sequence_id: sequenceId, seq_number: seqNumber },
                query: { target_frame_id: referenceFrameId, ego_frame_id: egoFrameId }
            }),
            enabled,
            placeholderData: (
                previous: TickEgoPositionView | undefined,
                previousQuery: Parameters<typeof keepPositionForSameFrames>[1]
            ) =>
                keepPositionForSameFrames(previous, previousQuery, { referenceFrameId, egoFrameId })
        };
    });
    return { query };
}
