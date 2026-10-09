import type { TickDetailView } from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, type CreateQueryResult } from '@tanstack/svelte-query';
import { getTickDetailsOptions } from './getTickDetailsOptions';

interface UseTickDetailsOptions {
    /** Getter for the dataset the sequence belongs to. */
    getDatasetId: () => string;
    /** Getter for the MCAP sequence to fetch the tick from. */
    getSequenceId: () => string;
    /** Getter for the position of the tick within the sequence. */
    getSeqNumber: () => number;
    /** Getter for the frame to express 3D cuboids in. Omit to keep each cuboid in its own frame. */
    getDisplayFrameId?: () => string | undefined;
}

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
}: UseTickDetailsOptions): { tickDetails: CreateQueryResult<TickDetailView, Error> } => {
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
