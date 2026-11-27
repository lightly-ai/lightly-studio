import { useQueryClient } from '@tanstack/svelte-query';
import { fromStore } from 'svelte/store';
import type { PointCloudWorkspaceContext } from '../provider/types';
import type { WorkspaceOptions } from '../workspaceOptions';
import type { useWorkspaceSceneData } from '../useWorkspaceSceneData/useWorkspaceSceneData.svelte';
import { useCreateCuboidAnnotation } from '../useCreateCuboidAnnotation';
import { useDeleteCuboidAnnotation } from '../useDeleteCuboidAnnotation';
import { useUpdateCuboidAnnotation } from '../useUpdateCuboidAnnotation';
import { useStartSequenceTrack } from '../useStartSequenceTrack';
import { useExtendSequenceTrack } from '../useExtendSequenceTrack';
import { useDeleteSequenceTrack } from '../useDeleteSequenceTrack';
import { useUpdateCuboidClass } from '../useUpdateCuboidClass';
import { getSequenceTracksSequenceQueryKey } from '../FrameTimeline/sequenceTracksQueryKey';
import { createCuboidTransformState } from '../CuboidLayer/cuboidTransformState';
import { createAnnotationIdMap } from '../cuboidUndo';
import { getTickDetailsSequenceQueryKey, useGlobalStorage } from '$lib/hooks';
import type { WorkspaceTool } from '../domain';
import type { CuboidBox } from '$lib/components/PointCloudLabelingWorkspace/CuboidDraft';
import type { CuboidTarget } from '../useCuboidTargetSource';

/** Shared annotation selection, tools, and persistence for every scene viewport. */
export function useWorkspaceEditing(
    getWorkspace: () => PointCloudWorkspaceContext,
    getOptions: () => WorkspaceOptions,
    getData: () => ReturnType<typeof useWorkspaceSceneData>,
    getIsEditingMode: () => boolean,
    getTarget: () => CuboidTarget
) {
    const queryClient = useQueryClient();
    // Track bars show which ticks have annotations, so refresh them when that changes.
    const refreshTracks = () =>
        queryClient.invalidateQueries({
            queryKey: getSequenceTracksSequenceQueryKey({
                datasetId: getOptions().datasetId,
                sequenceId: getOptions().sequenceId
            })
        });
    // Interpolation changes cuboids on other ticks too.
    const invalidateOtherTicks = () =>
        queryClient.invalidateQueries({
            queryKey: getTickDetailsSequenceQueryKey({
                datasetId: getOptions().datasetId,
                sequenceId: getOptions().sequenceId
            }),
            refetchType: 'none'
        });
    const { addReversibleAction } = useGlobalStorage();
    // Undo entries of this workspace find a cuboid that an undo of its delete re-created.
    const annotationIds = createAnnotationIdMap();
    // Undo bases the previous state on the persisted annotations, not on the scene snapshot,
    // which updates later in an effect.
    const getPersistedAnnotations = () => getWorkspace().tickDetails.data?.annotations ?? [];
    let selectedCuboidId = $state<string | null>(null);
    // Each tick has its own annotation IDs, so the selection follows the object track.
    let selectedTrackId: string | null = null;
    let hoveredCuboidId = $state<string | null>(null);
    let draftCuboid = $state.raw<CuboidBox | null>(null);
    let activeTool = $state<WorkspaceTool>('select');
    // The next cuboid placed with the create tool also starts a new object track.
    let addingTrack = $state(false);
    const {
        handleCreateCuboid: createCuboidAnnotation,
        showSelectClassDialog,
        handleClassSelected,
        handleClassDialogCancel,
        getRememberedLabel,
        labels,
        tracks
    } = useCreateCuboidAnnotation({
        getTarget,
        getCollectionId: () => getOptions().annotationSourceCollectionId,
        getDatasetId: () => getOptions().datasetId,
        getSequenceId: () => getOptions().sequenceId,
        getTickSampleId: () => {
            const { tick, snapshot } = getData();
            if (!tick || tick.isStale || snapshot?.tick !== getWorkspace().currentTick)
                return undefined;
            return tick.sampleId;
        },
        getSceneFrame: () => {
            const frame = getData().snapshot?.frame;
            return frame
                ? {
                      // Use the first channel's frameId — the top-level frameId on a merged
                      // frame is a comma-joined composite ("odom,odom") that does not match
                      // the per-channel frameIds used by the scene filter.
                      frameId: frame.channels[0]?.frameId ?? ''
                  }
                : null;
        }
    });

    const { handleCuboidTransform, waitForSaves } = useUpdateCuboidAnnotation({
        getCollectionId: () => getOptions().annotationSourceCollectionId,
        onUpdated: async () => {
            void refreshTracks();
            invalidateOtherTicks();
            await getWorkspace().tickDetails.refetch({ throwOnError: true });
        },
        getAnnotations: getPersistedAnnotations,
        annotationIds,
        addReversibleAction,
        onRestore: (annotationId) => transforms.discard(annotationId)
    });

    const { handleLabelChange } = useUpdateCuboidClass({
        getCollectionId: () => getOptions().annotationSourceCollectionId,
        getDatasetId: () => getOptions().datasetId,
        getSequenceId: () => getOptions().sequenceId,
        onUpdated: async () => {
            void refreshTracks();
            await getWorkspace().tickDetails.refetch({ throwOnError: true });
        },
        getAnnotations: getPersistedAnnotations,
        annotationIds,
        addReversibleAction
    });

    const { handleStartTrack } = useStartSequenceTrack({
        getDatasetId: () => getOptions().datasetId,
        getSequenceId: () => getOptions().sequenceId,
        onStarted: () => getWorkspace().tickDetails.refetch({ throwOnError: true })
    });

    const { handleExtendTrack } = useExtendSequenceTrack({
        getDatasetId: () => getOptions().datasetId,
        getSequenceId: () => getOptions().sequenceId,
        onExtended: () => getWorkspace().tickDetails.refetch({ throwOnError: true })
    });

    const { handleDeleteTrack: deleteTrack } = useDeleteSequenceTrack({
        getDatasetId: () => getOptions().datasetId,
        getSequenceId: () => getOptions().sequenceId,
        onDeleted: () => getWorkspace().tickDetails.refetch({ throwOnError: true })
    });

    async function handleDeleteTrack(params: {
        trackId: string;
        annotationSourceId: string;
        annotationIds: readonly string[];
    }): Promise<boolean> {
        const deleted = await deleteTrack(params);
        if (deleted && selectedCuboidId && params.annotationIds.includes(selectedCuboidId)) {
            selectCuboid(null);
        }
        return deleted;
    }

    function selectCuboid(cuboidId: string | null): void {
        selectedCuboidId = cuboidId;
        // A cuboid of a tick that is not loaded yet sets its track when the tick loads.
        selectedTrackId = getData().cuboids.find(({ id }) => id === cuboidId)?.trackId ?? null;
    }

    $effect(() => {
        const { cuboids } = getData();
        const selectedCuboid = cuboids.find(({ id }) => id === selectedCuboidId);
        if (selectedCuboid) {
            selectedTrackId = selectedCuboid.trackId;
            return;
        }
        if (!selectedTrackId) return;
        const trackCuboid = cuboids.find(({ trackId }) => trackId === selectedTrackId);
        if (trackCuboid) selectedCuboidId = trackCuboid.id;
    });

    const transforms = createCuboidTransformState({
        onTransform: (payload) => handleCuboidTransform(payload)
    });
    const { annotations } = transforms;

    $effect(() => {
        transforms.reconcile(getData().cuboids);
    });

    const panelCuboidTransform: typeof handleCuboidTransform = async (payload) => {
        await transforms.commit(payload);
        return true;
    };

    const { handleDeleteCuboid: deleteCuboidAnnotation } = useDeleteCuboidAnnotation({
        getCollectionId: () => getOptions().annotationSourceCollectionId,
        getAnnotations: getPersistedAnnotations,
        annotationIds,
        // The undo can restore the cuboid on a tick other than the active one.
        refresh: () =>
            Promise.all([
                refreshTracks(),
                queryClient.invalidateQueries({
                    queryKey: getTickDetailsSequenceQueryKey({
                        datasetId: getOptions().datasetId,
                        sequenceId: getOptions().sequenceId
                    })
                })
            ])
    });

    async function handleDeleteCuboid(cuboidId: string): Promise<void> {
        // The undo of the delete restores the cuboid with the geometry of its last save.
        await waitForSaves(cuboidId);
        // The delete rejects only when the refresh after a successful delete throws.
        const deleted = await deleteCuboidAnnotation(cuboidId).catch((error: unknown) => {
            deselectCuboid(cuboidId);
            throw error;
        });
        if (deleted) deselectCuboid(cuboidId);
    }

    function deselectCuboid(cuboidId: string): void {
        if (selectedCuboidId === cuboidId) selectCuboid(null);
    }

    async function handleCreateCuboid(box: CuboidBox, selectClass = false): Promise<void> {
        const asTrack = addingTrack;
        await createCuboidAnnotation(
            box,
            async (annotationId) => {
                // The first cuboid of a typed source creates the source, so list it.
                const sourceName = getTarget().targetSource;
                const isNewSource =
                    sourceName && !getData().annotationSourceNames?.includes(sourceName);
                if (isNewSource) void getData().refetchAnnotationSources();
                void refreshTracks();
                invalidateOtherTicks();
                await getWorkspace().tickDetails.refetch({ throwOnError: true });
                selectCuboid(annotationId);
                activeTool = 'select';
                addingTrack = false;
                // A failed attach leaves a plain cuboid, never an empty track.
                if (asTrack) await handleStartTrack(annotationId);
            },
            selectClass
        );
    }

    function setActiveTool(tool: WorkspaceTool): void {
        activeTool = tool;
        // Orthographic cameras fit a selected cuboid's frame, so drawing needs a world-aligned view.
        if (tool === 'create-cuboid') selectCuboid(null);
    }

    function toggleAddTrack(): void {
        addingTrack = !addingTrack;
        setActiveTool(addingTrack ? 'create-cuboid' : 'select');
    }

    async function handleTrackChange(): Promise<void> {
        void refreshTracks();
        invalidateOtherTicks();
        await getWorkspace().tickDetails.refetch({ throwOnError: true });
    }

    const occupiedTrackIds = $derived(
        new Set(getData().cuboids.flatMap((c) => (c.trackId ? [c.trackId] : [])))
    );

    const displayedAnnotations = fromStore(annotations);
    return {
        transforms,
        showSelectClassDialog,
        handleClassSelected,
        handleClassDialogCancel,
        getRememberedLabel,
        labels,
        tracks,
        get occupiedTrackIds() {
            return occupiedTrackIds;
        },
        get annotations() {
            return displayedAnnotations.current;
        },
        get selectedCuboidId() {
            return selectedCuboidId;
        },
        set selectedCuboidId(value) {
            selectCuboid(value);
        },
        get hoveredCuboidId() {
            return hoveredCuboidId;
        },
        set hoveredCuboidId(value) {
            hoveredCuboidId = value;
        },
        get draftCuboid() {
            return draftCuboid;
        },
        set draftCuboid(value) {
            draftCuboid = value;
        },
        get activeTool() {
            return activeTool;
        },
        set activeTool(value: WorkspaceTool) {
            setActiveTool(value);
            addingTrack = false;
        },
        get isAddingTrack() {
            return addingTrack && activeTool === 'create-cuboid';
        },
        toggleAddTrack,
        get effectiveTool() {
            return getIsEditingMode() ? activeTool : ('select' as const);
        },
        handleCreateCuboid,
        handleDeleteCuboid,
        handleStartTrack,
        handleExtendTrack,
        handleDeleteTrack,
        handleLabelChange,
        handleTrackChange,
        panelCuboidTransform
    };
}
