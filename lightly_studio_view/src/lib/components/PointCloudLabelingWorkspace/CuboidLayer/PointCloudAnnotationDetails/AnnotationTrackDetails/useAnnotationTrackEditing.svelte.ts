import { tick } from 'svelte';
import type { TrackWithClassNameView } from '$lib/api/lightly_studio_local';
import { createTrackEditingState } from './createTrackEditingState';
import { useTracks, useUpdateAnnotationsMutation, useUpdateTrackMutation } from '$lib/hooks';
import { usePointCloudWorkspaceLayoutContext } from '$lib/components/PointCloudLabelingWorkspace/pointCloudWorkspaceLayoutContext.svelte';
import { getParentTrackChoices } from './getParentTrackChoices';

interface Params {
    getAnnotation: () => { id: string; trackId: string | null; annotationSourceId: string };
    getOccupiedTrackIds: () => ReadonlySet<string>;
    onTrackChange: () => Promise<void>;
}

interface UseAnnotationTrackEditingReturn {
    readonly availableTracks: TrackWithClassNameView[];
    readonly parentTrackTracks: TrackWithClassNameView[];
    readonly currentTrack: TrackWithClassNameView | null | undefined;
    readonly isPending: boolean;
    state: ReturnType<typeof createTrackEditingState>;
    handleTrackChange: (trackId: string | null, isNewTrack: boolean) => Promise<void>;
    handleParentTrackChange: (parentTrackId: string | null) => Promise<void>;
}

export function useAnnotationTrackEditing({
    getAnnotation,
    getOccupiedTrackIds,
    onTrackChange
}: Params): UseAnnotationTrackEditingReturn {
    const annotation = $derived(getAnnotation());
    const occupiedTrackIds = $derived(getOccupiedTrackIds());
    const getLayoutState = usePointCloudWorkspaceLayoutContext();
    const tracksQuery = useTracks(() => getLayoutState().datasetId);
    const tracks = $derived(tracksQuery.data ?? []);

    const { updateAnnotations } = useUpdateAnnotationsMutation({
        getCollectionId: () => annotation.annotationSourceId
    });

    const trackMutation = useUpdateTrackMutation({
        getDatasetId: () => getLayoutState().datasetId
    });

    const state = createTrackEditingState({ refresh });

    const availableTracks = $derived(
        tracks.filter(
            (t) =>
                !occupiedTrackIds.has(t.object_track_id) || t.object_track_id === annotation.trackId
        )
    );
    const currentTrack = $derived(
        annotation.trackId ? tracks.find((t) => t.object_track_id === annotation.trackId) : null
    );
    const parentTrackTracks = $derived(getParentTrackChoices(tracks, annotation.trackId));

    async function refresh(): Promise<void> {
        const results = await Promise.allSettled([
            tracksQuery.refetch({ throwOnError: true }),
            onTrackChange()
        ]);
        const failure = results.find((result) => result.status === 'rejected');
        if (failure?.status === 'rejected') throw failure.reason;
        await tick();
        if (
            annotation.trackId &&
            !tracksQuery.data?.some((track) => track.object_track_id === annotation.trackId)
        )
            throw new Error('The annotation track is not available after refresh.');
    }

    async function handleTrackChange(trackId: string | null, isNewTrack: boolean): Promise<void> {
        await state.save(() =>
            updateAnnotations([
                {
                    annotation_id: annotation.id,
                    collection_id: annotation.annotationSourceId,
                    ...(isNewTrack ? { create_new_track: true } : { object_track_id: trackId })
                }
            ])
        );
    }

    async function handleParentTrackChange(parentTrackId: string | null): Promise<void> {
        const trackId = annotation.trackId;
        if (!trackId) return;
        await state.save(() => trackMutation.updateParentTrack(trackId, parentTrackId));
    }
    return {
        get availableTracks() {
            return availableTracks;
        },
        get parentTrackTracks() {
            return parentTrackTracks;
        },
        get currentTrack() {
            return currentTrack;
        },
        get isPending() {
            return trackMutation.isPending;
        },
        state,
        handleTrackChange,
        handleParentTrackChange
    };
}
