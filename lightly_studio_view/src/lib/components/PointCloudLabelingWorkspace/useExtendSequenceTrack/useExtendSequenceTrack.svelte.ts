import { extendSequenceTrackMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { getTickDetailsSequenceQueryKey } from '$lib/hooks/useTickDetails/getTickDetailsOptions';
import { createMutation, useQueryClient } from '@tanstack/svelte-query';
import { toast } from 'svelte-sonner';
import { getSequenceTracksSequenceQueryKey } from '../FrameTimeline/sequenceTracksQueryKey';

interface Params {
    getDatasetId: () => string;
    getSequenceId: () => string;
    /** Refreshes the active tick after annotations were added to it. */
    onExtended: () => Promise<unknown>;
}

interface ExtendParams {
    trackId: string;
    annotationSourceId: string;
    startSeqNumber: number;
    endSeqNumber: number;
}

/** Extends an object track outward by copying its boundary cuboids onto more ticks. */
export function useExtendSequenceTrack({ getDatasetId, getSequenceId, onExtended }: Params) {
    const mutation = createMutation(() => extendSequenceTrackMutation());
    const queryClient = useQueryClient();
    let isExtending = false;

    async function handleExtendTrack(params: ExtendParams): Promise<boolean> {
        if (isExtending) return false;
        isExtending = true;
        try {
            await mutation.mutateAsync({
                path: {
                    dataset_id: getDatasetId(),
                    sequence_id: getSequenceId(),
                    track_id: params.trackId
                },
                body: {
                    annotation_source_id: params.annotationSourceId,
                    start_seq_number: params.startSeqNumber,
                    end_seq_number: params.endSeqNumber
                }
            });
        } catch {
            toast.error('Failed to extend the track. Please try again.');
            return false;
        } finally {
            isExtending = false;
        }
        const sequence = { datasetId: getDatasetId(), sequenceId: getSequenceId() };
        // Prefetched ticks hold annotation data too, so refresh every tick of the sequence.
        void queryClient.invalidateQueries({
            queryKey: getSequenceTracksSequenceQueryKey(sequence)
        });
        void queryClient.invalidateQueries({ queryKey: getTickDetailsSequenceQueryKey(sequence) });
        try {
            await onExtended();
        } catch {
            toast.error('Track extended, but the workspace could not refresh. Please try again.');
        }
        return true;
    }

    return { handleExtendTrack };
}
