import { updateParentTrackMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation } from '@tanstack/svelte-query';

interface Params {
    getDatasetId: () => string;
}

interface UseUpdateTrackMutationReturn {
    updateParentTrack: (trackId: string, parentTrackId: string | null) => Promise<void>;
    readonly isPending: boolean;
}

export function useUpdateTrackMutation({ getDatasetId }: Params): UseUpdateTrackMutationReturn {
    const mutation = createMutation(() => updateParentTrackMutation());

    async function updateParentTrack(trackId: string, parentTrackId: string | null): Promise<void> {
        const datasetId = getDatasetId();
        await mutation.mutateAsync({
            path: { dataset_id: datasetId, track_id: trackId },
            body: { parent_object_track_id: parentTrackId }
        });
    }

    return {
        updateParentTrack,
        get isPending() {
            return mutation.isPending;
        }
    };
}
