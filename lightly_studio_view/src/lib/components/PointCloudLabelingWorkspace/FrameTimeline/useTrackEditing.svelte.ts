import { extendTrack, startTrack } from '$lib/api/lightly_studio_local/sdk.gen';
import { toast } from 'svelte-sonner';

interface TrackIds {
    datasetId: string;
    sequenceId: string;
}

/** Saves track edits and refreshes the active tick and sequence timeline. */
export function useTrackEditing(getIds: () => TrackIds, onSaved: () => Promise<unknown>) {
    let saving = $state(false);

    async function start(annotationId: string): Promise<string | null> {
        if (saving) return null;
        saving = true;
        try {
            const { datasetId, sequenceId } = getIds();
            const { data, error } = await startTrack({
                path: { dataset_id: datasetId, sequence_id: sequenceId },
                body: { annotation_id: annotationId }
            });
            if (error || !data) throw new Error('Could not start the track.');
            await onSaved();
            toast.success('Object track started');
            return data.object_track_id;
        } catch {
            toast.error('Could not start the track. Please try again.');
            return null;
        } finally {
            saving = false;
        }
    }

    async function extend(
        trackId: string,
        annotationId: string,
        mode: 'hold' | 'interpolate'
    ): Promise<void> {
        if (saving) return;
        saving = true;
        try {
            const { datasetId, sequenceId } = getIds();
            const { error } = await extendTrack({
                path: { dataset_id: datasetId, sequence_id: sequenceId, track_id: trackId },
                body: { annotation_id: annotationId, mode }
            });
            if (error) throw new Error('Could not add the keyframe.');
            await onSaved();
            toast.success('Keyframe added');
        } catch {
            toast.error('Could not add the keyframe. Check its class, source, and position.');
        } finally {
            saving = false;
        }
    }

    return {
        start,
        extend,
        get saving() {
            return saving;
        }
    };
}
