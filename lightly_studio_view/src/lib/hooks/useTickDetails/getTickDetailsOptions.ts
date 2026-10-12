import { getTickDetailsQueryKey } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { getTickDetails } from '$lib/api/lightly_studio_local/sdk.gen';
import type { TickDetailView } from '$lib/api/lightly_studio_local/types.gen';

interface TickDetailsOptions {
    datasetId: string;
    sequenceId: string;
    seqNumber: number;
    displayFrameId?: string;
}

/** Builds the query used by both the visible tick and playback prefetch. */
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
}
