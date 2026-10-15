import type { TickDetailView } from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, type CreateQueryResult } from '@tanstack/svelte-query';
import { getTickDetailsOptions } from './getTickDetailsOptions';

/**
 * Fetches the channel locators and annotations for one tick of a sequence.
 *
 * If the 3D cuboids cannot be mapped to `displayFrameId`, e.g. at a gap in `/tf`, the tick
 * is loaded with each cuboid in its own frame instead, which the `frame_id` of each cuboid
 * shows.
 */
export const useTickDetails = ({
    getDatasetId,
    getSequenceId,
    getSeqNumber,
    getDisplayFrameId = () => undefined
}: {
    getDatasetId: () => string;
    getSequenceId: () => string;
    getSeqNumber: () => number;
    /** Frame to express the 3D cuboids in. Omit to keep each cuboid in its own frame. */
    getDisplayFrameId?: () => string | undefined;
}): { tickDetails: CreateQueryResult<TickDetailView, Error> } => {
    const tickDetails = createQuery(() => {
        const datasetId = getDatasetId();
        const sequenceId = getSequenceId();
        const displayFrameId = getDisplayFrameId();
        return {
            ...getTickDetailsOptions({
                datasetId,
                sequenceId,
                seqNumber: getSeqNumber(),
                displayFrameId
            }),
            enabled: Boolean(datasetId) && Boolean(sequenceId),
            placeholderData: (previous: TickDetailView | undefined) => previous
        };
    });

    return { tickDetails };
};
