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
import type { WorkspaceTool } from '../domain';
import type { CuboidBox } from '$lib/components/PointCloudLabelingWorkspace/CuboidDraft';

/** Shared annotation selection, tools, and persistence for every scene viewport. */
export function useWorkspaceEditing(
    getWorkspace: () => PointCloudWorkspaceContext,
    getOptions: () => WorkspaceOptions,
    getData: () => ReturnType<typeof useWorkspaceSceneData>,
    getIsEditingMode: () => boolean
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
    let selectedCuboidId = $state<string | null>(null);
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
        labels
    } = useCreateCuboidAnnotation({
        getCollectionId: () => getOptions().annotationSourceCollectionId,
        getDatasetId: () => getOptions().datasetId,
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

    const { handleCuboidTransform } = useUpdateCuboidAnnotation({
        getCollectionId: () => getOptions().annotationSourceCollectionId,
        onUpdated: async () => {
            void refreshTracks();
            await getWorkspace().tickDetails.refetch({ throwOnError: true });
        }
    });

    const { handleLabelChange } = useUpdateCuboidClass({
        getCollectionId: () => getOptions().annotationSourceCollectionId,
        getDatasetId: () => getOptions().datasetId,
        getSequenceId: () => getOptions().sequenceId,
        onUpdated: async () => {
            void refreshTracks();
            await getWorkspace().tickDetails.refetch({ throwOnError: true });
        }
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
            selectedCuboidId = null;
        }
        return deleted;
    }

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
        getAnnotations: () => getData().snapshot?.annotations ?? []
    });

    async function handleDeleteCuboid(cuboidId: string): Promise<void> {
        const deleted = await deleteCuboidAnnotation(cuboidId);
        if (!deleted) return;
        void refreshTracks();
        await getWorkspace().tickDetails.refetch();
        if (selectedCuboidId === cuboidId) {
            selectedCuboidId = null;
        }
    }

    async function handleCreateCuboid(box: CuboidBox, selectClass = false): Promise<void> {
        const asTrack = addingTrack;
        await createCuboidAnnotation(
            box,
            async (annotationId) => {
                await getWorkspace().tickDetails.refetch({ throwOnError: true });
                selectedCuboidId = annotationId;
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
        if (tool === 'create-cuboid') selectedCuboidId = null;
    }

    function toggleAddTrack(): void {
        addingTrack = !addingTrack;
        setActiveTool(addingTrack ? 'create-cuboid' : 'select');
    }

    const displayedAnnotations = fromStore(annotations);
    return {
        transforms,
        showSelectClassDialog,
        handleClassSelected,
        handleClassDialogCancel,
        labels,
        get annotations() {
            return displayedAnnotations.current;
        },
        get selectedCuboidId() {
            return selectedCuboidId;
        },
        set selectedCuboidId(value) {
            selectedCuboidId = value;
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
        panelCuboidTransform
    };
}
