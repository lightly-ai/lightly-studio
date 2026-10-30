import { fromStore } from 'svelte/store';
import type { PointCloudWorkspaceContext } from '../provider/types';
import type { WorkspaceOptions } from '../workspaceOptions';
import type { useWorkspaceSceneData } from '../useWorkspaceSceneData/useWorkspaceSceneData.svelte';
import { useCreateCuboidAnnotation } from '../useCreateCuboidAnnotation';
import { useDeleteCuboidAnnotation } from '../useDeleteCuboidAnnotation';
import { useUpdateCuboidAnnotation } from '../useUpdateCuboidAnnotation';
import { useUpdateCuboidClass } from '../useUpdateCuboidClass';
import { createCuboidTransformState } from '../CuboidLayer/cuboidTransformState';
import type { Vector3, WorkspaceTool } from '../domain';

/** Shared annotation selection, tools, and persistence for every scene viewport. */
export function useWorkspaceEditing(
    getWorkspace: () => PointCloudWorkspaceContext,
    getOptions: () => WorkspaceOptions,
    getData: () => ReturnType<typeof useWorkspaceSceneData>,
    getIsEditingMode: () => boolean
) {
    let selectedCuboidId = $state<string | null>(null);
    let hoveredCuboidId = $state<string | null>(null);
    let activeTool = $state<WorkspaceTool>('select');
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
                      bounds: frame.bounds,
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
        onUpdated: () => getWorkspace().tickDetails.refetch({ throwOnError: true })
    });

    const { handleLabelChange } = useUpdateCuboidClass({
        getCollectionId: () => getOptions().annotationSourceCollectionId,
        getDatasetId: () => getOptions().datasetId,
        getSequenceId: () => getOptions().sequenceId,
        onUpdated: () => getWorkspace().tickDetails.refetch({ throwOnError: true })
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
        getAnnotations: () => getData().snapshot?.annotations ?? []
    });

    async function handleDeleteCuboid(cuboidId: string): Promise<void> {
        const deleted = await deleteCuboidAnnotation(cuboidId);
        if (!deleted) return;
        await getWorkspace().tickDetails.refetch();
        if (selectedCuboidId === cuboidId) {
            selectedCuboidId = null;
        }
    }

    async function handleCreateCuboid(groundPosition: Vector3): Promise<void> {
        await createCuboidAnnotation(groundPosition, async (annotationId) => {
            await getWorkspace().tickDetails.refetch({ throwOnError: true });
            selectedCuboidId = annotationId;
            activeTool = 'select';
        });
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
        get activeTool() {
            return activeTool;
        },
        set activeTool(value: WorkspaceTool) {
            activeTool = value;
        },
        get effectiveTool() {
            return getIsEditingMode() ? activeTool : ('select' as const);
        },
        handleCreateCuboid,
        handleDeleteCuboid,
        handleLabelChange,
        panelCuboidTransform
    };
}
