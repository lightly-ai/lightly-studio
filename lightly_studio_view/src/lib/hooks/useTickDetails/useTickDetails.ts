import { getTickDetailsQueryKey } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { getTickDetails } from '$lib/api/lightly_studio_local/sdk.gen';
import type { TickDetailView } from '$lib/api/lightly_studio_local/types.gen';
import { createQuery, type CreateQueryResult } from '@tanstack/svelte-query';

/**
 * Fetches the channel locators and annotations for one tick of a sequence.
 *
 * If the 3D cuboids cannot be mapped to `targetFrameId`, e.g. at a gap in `/tf`, the tick
 * is loaded with each cuboid in its own frame instead, which the `frame_id` of each cuboid
 * shows.
 */
export const useTickDetails = ({
    getDatasetId,
    getSequenceId,
    getSeqNumber,
    getTargetFrameId = () => undefined
}: {
    getDatasetId: () => string;
    getSequenceId: () => string;
    getSeqNumber: () => number;
    /** Frame to express the 3D cuboids in. Omit to keep each cuboid in its own frame. */
    getTargetFrameId?: () => string | undefined;
}): { tickDetails: CreateQueryResult<TickDetailView, Error> } => {
    const tickDetails = createQuery(() => {
        const datasetId = getDatasetId();
        const sequenceId = getSequenceId();
        const targetFrameId = getTargetFrameId();
        const path = {
            dataset_id: datasetId,
            sequence_id: sequenceId,
            seq_number: getSeqNumber()
        };
        return {
            queryKey: getTickDetailsQueryKey({
                path,
                ...(targetFrameId ? { query: { target_frame_id: targetFrameId } } : {})
            }),
            queryFn: async ({ signal }: { signal: AbortSignal }): Promise<TickDetailView> => {
                try {
                    return await fetchTickDetails({ path, targetFrameId, signal });
                } catch (error) {
                    // A tick without a transform to the target frame still loads, so that
                    // its channels can be shown.
                    if (!targetFrameId || signal.aborted || !isTransformUnavailable(error)) {
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
    targetFrameId,
    signal
}: {
    path: { dataset_id: string; sequence_id: string; seq_number: number };
    targetFrameId?: string;
    signal: AbortSignal;
}): Promise<TickDetailView> {
    const { data } = await getTickDetails({
        path,
        ...(targetFrameId ? { query: { target_frame_id: targetFrameId } } : {}),
        signal,
        throwOnError: true
    });
    return data;
}
