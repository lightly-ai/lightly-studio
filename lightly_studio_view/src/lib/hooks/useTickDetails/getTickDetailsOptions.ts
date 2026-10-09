import { getTickDetailsQueryKey } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { getTickDetails } from '$lib/api/lightly_studio_local/sdk.gen';
import type { TickDetailView } from '$lib/api/lightly_studio_local/types.gen';

interface TickDetailsOptions {
    /** Dataset the sequence belongs to. */
    datasetId: string;
    /** MCAP sequence to fetch the tick from. */
    sequenceId: string;
    /** Position of the tick within the sequence. */
    seqNumber: number;
    /** Frame to express the 3D cuboids in. Omit to keep each cuboid in its own frame. */
    displayFrameId?: string;
}

/** Builds the query used by both the visible tick and playback lookahead. */
export function getTickDetailsOptions({
    datasetId,
    sequenceId,
    seqNumber,
    displayFrameId
}: TickDetailsOptions) {
    const path = {
        dataset_id: datasetId,
        sequence_id: sequenceId,
        seq_number: seqNumber
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
                if (!displayFrameId || signal.aborted || !isTransformUnavailable(error)) {
                    throw error;
                }
                return fetchTickDetails({ path, signal });
            }
        }
    };
}

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
