import { getTickDetailsOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import type { TickDetailView } from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, keepPreviousData, type CreateQueryResult } from '@tanstack/svelte-query';

export const useTickDetails = ({
    getDatasetId,
    getSequenceId,
    getSeqNumber,
    getTargetFrameId = () => undefined
}: {
    getDatasetId: () => string;
    getSequenceId: () => string;
    getSeqNumber: () => number;
    /** Frame to express the 3D cuboids in; omit to keep each cuboid in its own frame. */
    getTargetFrameId?: () => string | undefined;
}): { tickDetails: CreateQueryResult<TickDetailView, Error> } => {
    const tickDetails = createQuery(() => {
        const datasetId = getDatasetId();
        const sequenceId = getSequenceId();
        const targetFrameId = getTargetFrameId();
        return {
            ...getTickDetailsOptions({
                path: {
                    dataset_id: datasetId,
                    sequence_id: sequenceId,
                    seq_number: getSeqNumber()
                },
                ...(targetFrameId ? { query: { target_frame_id: targetFrameId } } : {})
            }),
            enabled: Boolean(datasetId) && Boolean(sequenceId),
            // Keep the previous tick while the next one loads, so stepping does not flash a spinner.
            placeholderData: keepPreviousData
        };
    });

    return { tickDetails };
};
