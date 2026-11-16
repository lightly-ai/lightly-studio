import { deleteSequenceTrackMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { getTickDetailsSequenceQueryKey } from '$lib/hooks/useTickDetails/getTickDetailsOptions';
import { createMutation, useQueryClient } from '@tanstack/svelte-query';
import { toast } from 'svelte-sonner';
import { getSequenceTracksSequenceQueryKey } from '../FrameTimeline/sequenceTracksQueryKey';

interface Params {
    getDatasetId: () => string;
    getSequenceId: () => string;
    /** Refreshes the active tick after the track's cuboids were deleted. */
    onDeleted: () => Promise<unknown>;
}

interface DeleteParams {
    trackId: string;
    annotationSourceId: string;
}

/** Deletes an object track together with its cuboids. */
export function useDeleteSequenceTrack({ getDatasetId, getSequenceId, onDeleted }: Params) {
    const mutation = createMutation(() => deleteSequenceTrackMutation());
    const queryClient = useQueryClient();
    let isDeleting = false;

    /** Resolves to whether the track was deleted; failures are reported with a toast. */
    async function handleDeleteTrack({ trackId, annotationSourceId }: DeleteParams) {
        if (isDeleting) return false;
        isDeleting = true;
        try {
            await mutation.mutateAsync({
                path: {
                    dataset_id: getDatasetId(),
                    sequence_id: getSequenceId(),
                    track_id: trackId
                },
                query: { annotation_source_id: annotationSourceId }
            });
        } catch {
            toast.error('Failed to delete the track. Please try again.');
            return false;
        } finally {
            isDeleting = false;
        }
        const sequence = { datasetId: getDatasetId(), sequenceId: getSequenceId() };
        void queryClient.invalidateQueries({
            queryKey: getSequenceTracksSequenceQueryKey(sequence)
        });
        void queryClient.invalidateQueries({ queryKey: getTickDetailsSequenceQueryKey(sequence) });
        try {
            await onDeleted();
        } catch {
            toast.error('Track deleted, but the workspace could not refresh. Please try again.');
        }
        return true;
    }

    return { handleDeleteTrack };
}
