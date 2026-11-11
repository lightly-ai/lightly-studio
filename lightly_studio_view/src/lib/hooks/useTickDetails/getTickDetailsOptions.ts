import { getTickDetailsQueryKey } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { getTickDetails } from '$lib/api/lightly_studio_local/sdk.gen';
import type { TickDetailView } from '$lib/api/lightly_studio_local/types.gen';

interface TickDetailsSequenceParams {
    /** Dataset that owns the sequence. */
    datasetId: string;
    /** Sequence whose tick details should be fetched. */
    sequenceId: string;
}

interface TickDetailsOptionsParams extends TickDetailsSequenceParams {
    /** Zero-based tick position in the sequence. */
    seqNumber: number;
    /** Optional target frame for transforming annotations. */
    displayFrameId?: string;
}

/**
 * A partial query key that matches all tick-details queries for the given dataset and
 * sequence, regardless of tick number or display frame. Use with
 * `queryClient.invalidateQueries` after a mutation that affects annotations across all
 * ticks in a sequence (e.g. re-labeling an object track).
 */
export const getTickDetailsSequenceQueryKey = ({
    datasetId,
    sequenceId
}: TickDetailsSequenceParams) => [
    { _id: 'getTickDetails', path: { dataset_id: datasetId, sequence_id: sequenceId } }
];

/** Builds the tick-details query used by both the visible workspace and prefetching. */
export const getTickDetailsOptions = ({
    datasetId,
    sequenceId,
    seqNumber,
    displayFrameId
}: TickDetailsOptionsParams) => {
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
                const { data } = await getTickDetails({
                    path,
                    ...(displayFrameId ? { query: { target_frame_id: displayFrameId } } : {}),
                    signal,
                    throwOnError: true
                });
                return data;
            } catch (error) {
                const detail = (error as { detail?: { type?: unknown } } | null)?.detail;
                if (!displayFrameId || signal.aborted || detail?.type !== 'transform_unavailable') {
                    throw error;
                }
                const { data } = await getTickDetails({ path, signal, throwOnError: true });
                return data;
            }
        }
    };
};
