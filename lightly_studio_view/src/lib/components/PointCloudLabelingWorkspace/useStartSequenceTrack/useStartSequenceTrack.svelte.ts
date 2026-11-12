import { startSequenceTrackMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { getTickDetailsSequenceQueryKey } from '$lib/hooks/useTickDetails/getTickDetailsOptions';
import { createMutation, useQueryClient } from '@tanstack/svelte-query';
import { toast } from 'svelte-sonner';
import { getSequenceTracksSequenceQueryKey } from '../FrameTimeline/sequenceTracksQueryKey';

interface Params {
    getDatasetId: () => string;
    getSequenceId: () => string;
    /** Refreshes the active tick after the cuboid joined its new track. */
    onStarted: () => Promise<unknown>;
}

/** Creates an object track from an untracked cuboid. */
export function useStartSequenceTrack({ getDatasetId, getSequenceId, onStarted }: Params) {
    const mutation = createMutation(() => startSequenceTrackMutation());
    const queryClient = useQueryClient();
    let isStarting = false;

    async function handleStartTrack(annotationId: string): Promise<boolean> {
        if (isStarting) return false;
        isStarting = true;
        try {
            await mutation.mutateAsync({
                path: { dataset_id: getDatasetId(), sequence_id: getSequenceId() },
                body: { annotation_id: annotationId }
            });
        } catch {
            toast.error('Failed to start the track. Please try again.');
            return false;
        } finally {
            isStarting = false;
        }
        const sequence = { datasetId: getDatasetId(), sequenceId: getSequenceId() };
        void queryClient.invalidateQueries({
            queryKey: getSequenceTracksSequenceQueryKey(sequence)
        });
        void queryClient.invalidateQueries({ queryKey: getTickDetailsSequenceQueryKey(sequence) });
        try {
            await onStarted();
        } catch {
            toast.error('Track started, but the workspace could not refresh. Please try again.');
        }
        return true;
    }

    return { handleStartTrack };
}
