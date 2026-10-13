import { getTickDetailsQueryKey } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { getTickDetails } from '$lib/api/lightly_studio_local/sdk.gen';
import type { TickDetailView } from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, type CreateQueryResult } from '@tanstack/svelte-query';

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
        const path = {
            dataset_id: datasetId,
            sequence_id: sequenceId,
            seq_number: getSeqNumber()
        };
        return {
            queryKey: getTickDetailsQueryKey({
                path,
                ...(displayFrameId ? { query: { target_frame_id: displayFrameId } } : {})
            }),
            queryFn: async ({ signal }: { signal: AbortSignal }): Promise<TickDetailView> => {
                try {
                    return await fetchTickDetails({ path, displayFrameId, signal });
                } catch (error) {
                    // A tick without a transform to the target frame still loads, so that
                    // its channels can be shown.
                    if (!displayFrameId || signal.aborted || !isTransformUnavailable(error)) {
                        throw error;
                    }
                    return fetchTickDetails({ path, signal });
                }
            },
            enabled: Boolean(datasetId) && Boolean(sequenceId),
            placeholderData: (previous: TickDetailView | undefined) => previous
        };
    });

    return { tickDetails };
};

// The `detail.type` the backend sets if no transform connects the cuboid frames to the target.
const TRANSFORM_UNAVAILABLE_ERROR_TYPE = 'transform_unavailable';

function isTransformUnavailable(error: unknown): boolean {
    const detail = (error as { detail?: { type?: unknown } } | null)?.detail;
    return detail?.type === TRANSFORM_UNAVAILABLE_ERROR_TYPE;
}

async function fetchTickDetails({
    path,
    displayFrameId,
    signal
}: {
    path: { dataset_id: string; sequence_id: string; seq_number: number };
    displayFrameId?: string;
    signal: AbortSignal;
}): Promise<TickDetailView> {
    const { data } = await getTickDetails({
        path,
        ...(displayFrameId ? { query: { target_frame_id: displayFrameId } } : {}),
        signal,
        throwOnError: true
    });
    return data;
}
