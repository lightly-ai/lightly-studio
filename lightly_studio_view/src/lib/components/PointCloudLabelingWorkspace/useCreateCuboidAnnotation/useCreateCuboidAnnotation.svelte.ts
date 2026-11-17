import {
    AnnotationClassNotAvailableError,
    getCreateLabelErrorMessage,
    useAnnotationLabels,
    useCreateAnnotation,
    useCreateLabel,
    useGlobalStorage,
    useSelectClassDialog
} from '$lib/hooks';
import { get } from 'svelte/store';
import { toast } from 'svelte-sonner';
import type { AnnotationCreateInput } from '$lib/api/lightly_studio_local';
import type { CuboidBox } from '$lib/components/PointCloudLabelingWorkspace/CuboidDraft';
import { CUBOID_SOURCE_MESSAGES, type CuboidTarget } from '../useCuboidTargetSource';

interface SceneFrame {
    frameId: string;
}

interface Params {
    /** The annotation source new cuboids go to. */
    getTarget: () => CuboidTarget;
    getCollectionId: () => string | undefined;
    getDatasetId: () => string;
    getTickSampleId: () => string | undefined;
    getSceneFrame: () => SceneFrame | null;
}

interface CreateCuboidParams {
    frame: SceneFrame | null;
    box: CuboidBox;
    labelId: string;
    sampleId: string;
    sourceName: string;
}

interface UseCreateCuboidAnnotationReturn {
    handleCreateCuboid: (
        box: CuboidBox,
        onCreated: (annotationId: string) => void | Promise<void>,
        selectClass?: boolean
    ) => Promise<void>;
    showSelectClassDialog: ReturnType<typeof useSelectClassDialog>['open'];
    handleClassSelected: ReturnType<typeof useSelectClassDialog>['handleConfirm'];
    handleClassDialogCancel: ReturnType<typeof useSelectClassDialog>['handleCancel'];
    labels: ReturnType<typeof useAnnotationLabels>;
}

function buildCuboidInput({
    frame,
    box,
    labelId,
    sampleId,
    sourceName
}: CreateCuboidParams): AnnotationCreateInput {
    return {
        parent_sample_id: sampleId,
        annotation_type: 'cuboid_3d',
        annotation_label_id: labelId,
        annotation_collection_name: sourceName,
        cuboid_3d: {
            frame_id: frame?.frameId ?? '',
            px: box.center[0],
            py: box.center[1],
            pz: box.center[2],
            // The heading is a rotation around the vertical axis.
            qx: 0,
            qy: 0,
            qz: Math.sin(box.yaw / 2),
            qw: Math.cos(box.yaw / 2),
            sx: box.size[0],
            sy: box.size[1],
            sz: box.size[2]
        }
    };
}

/** Creates point-cloud cuboids using the last selected annotation class when available. */
export function useCreateCuboidAnnotation({
    getTarget,
    getCollectionId,
    getDatasetId,
    getTickSampleId,
    getSceneFrame
}: Params): UseCreateCuboidAnnotationReturn {
    const {
        open: showSelectClassDialog,
        requestLabel,
        handleConfirm: handleClassSelected,
        handleCancel: handleClassDialogCancel
    } = useSelectClassDialog();
    const { createLabel } = useCreateLabel({ getCollectionId: () => getCollectionId() ?? '' });
    const { createAnnotation } = useCreateAnnotation({
        getCollectionId: () => getCollectionId() ?? ''
    });
    const labels = useAnnotationLabels(() => ({ collectionId: getCollectionId() ?? '' }));
    const { lastAnnotationLabel, updateLastAnnotationLabel } = useGlobalStorage();

    async function selectAnnotationLabel(
        collectionId: string,
        selectClass: boolean
    ): Promise<string | null> {
        const stored = get(lastAnnotationLabel)[collectionId] ?? null;
        if (stored && !selectClass) return stored;
        const selection = await requestLabel();
        if (!selection?.label) return null;
        updateLastAnnotationLabel(collectionId, selection.label);
        return selection.label;
    }

    function forgetLastAnnotationLabel(collectionId: string) {
        lastAnnotationLabel.update((value) => {
            delete value[collectionId];
            return value;
        });
    }

    async function findOrCreateLabelId(
        collectionId: string,
        labelName: string
    ): Promise<string | null> {
        let currentData = labels.data;
        if (currentData === undefined) {
            const result = await labels.refetch();
            if (result.isError || result.data === undefined) return null;
            currentData = result.data;
        }
        const existingLabel = currentData?.find(
            (label) => label.annotation_label_name === labelName
        );
        if (existingLabel?.annotation_label_id) return existingLabel.annotation_label_id;
        try {
            const label = await createLabel({
                dataset_id: getDatasetId(),
                annotation_label_name: labelName
            });
            await labels.refetch();
            return label.annotation_label_id ?? null;
        } catch (error) {
            // Forget a rejected class, so the next attempt asks for a class again.
            if (error instanceof AnnotationClassNotAvailableError) {
                forgetLastAnnotationLabel(collectionId);
            }
            toast.error(
                getCreateLabelErrorMessage(
                    error,
                    'Failed to create annotation class. Please try again.'
                )
            );
            return null;
        }
    }

    async function saveCuboid(params: CreateCuboidParams): Promise<string> {
        const annotation = await createAnnotation(buildCuboidInput(params));
        toast.success(`Cuboid added to ${params.sourceName}`);
        return annotation.sample_id;
    }

    /** Returns the source for a new cuboid, or null after telling the user why there is none. */
    function getTargetSourceOrExplain(): string | null {
        const { targetSource, blockedReason, needsPick } = getTarget();
        if (blockedReason) toast.error(blockedReason);
        else if (needsPick) toast.error(CUBOID_SOURCE_MESSAGES.pick);
        return targetSource;
    }

    async function handleCreateCuboid(
        box: CuboidBox,
        onCreated: (annotationId: string) => void | Promise<void>,
        selectClass = false
    ): Promise<void> {
        const collectionId = getCollectionId();
        const sampleId = getTickSampleId();
        const capturedFrame = getSceneFrame();
        if (!collectionId || !sampleId) return;
        if (!getTargetSourceOrExplain()) return;
        const labelName = await selectAnnotationLabel(collectionId, selectClass);
        if (!labelName) return;
        // Cancel if the active tick changed while the class dialog was open.
        if (getTickSampleId() !== sampleId) return;
        const labelId = await findOrCreateLabelId(collectionId, labelName);
        if (!labelId) return;
        // Cancel if the active sample or collection changed while finding/creating the label.
        if (getTickSampleId() !== sampleId || getCollectionId() !== collectionId) return;
        // The user can change the source while the class dialog is open.
        const sourceName = getTargetSourceOrExplain();
        if (!sourceName) return;
        let annotationId: string;
        try {
            annotationId = await saveCuboid({
                frame: capturedFrame,
                box,
                labelId,
                sampleId,
                sourceName
            });
        } catch {
            toast.error('Failed to create annotation. Please try again.');
            return;
        }
        try {
            await onCreated(annotationId);
        } catch {
            toast.error(
                'Annotation created, but the workspace could not refresh. Please try again.'
            );
        }
    }

    return {
        handleCreateCuboid,
        showSelectClassDialog,
        handleClassSelected,
        handleClassDialogCancel,
        labels
    };
}
