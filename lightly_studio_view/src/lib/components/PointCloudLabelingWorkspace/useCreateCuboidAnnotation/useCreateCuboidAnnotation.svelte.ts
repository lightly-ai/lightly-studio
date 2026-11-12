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
import type { Bounds3 } from '$lib/components/PointCloudLabelingWorkspace/domain';
import {
    getDefaultCuboidBox,
    type CuboidBox,
    type CuboidPlacement
} from '$lib/components/PointCloudLabelingWorkspace/CuboidDraft/cuboidDraft';

interface SceneFrame {
    bounds: Bounds3 | null;
    frameId: string;
}

interface Params {
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
}

interface UseCreateCuboidAnnotationReturn {
    handleCreateCuboid: (
        placement: CuboidPlacement,
        onCreated: (annotationId: string) => void | Promise<void>
    ) => Promise<void>;
    showSelectClassDialog: ReturnType<typeof useSelectClassDialog>['open'];
    handleClassSelected: ReturnType<typeof useSelectClassDialog>['handleConfirm'];
    handleClassDialogCancel: ReturnType<typeof useSelectClassDialog>['handleCancel'];
    labels: ReturnType<typeof useAnnotationLabels>;
}

const ZERO_BOUNDS: Bounds3 = { min: [0, 0, 0], max: [0, 0, 0] };

function buildCuboidInput({
    frame,
    box,
    labelId,
    sampleId
}: CreateCuboidParams): AnnotationCreateInput {
    return {
        parent_sample_id: sampleId,
        annotation_type: 'cuboid_3d',
        annotation_label_id: labelId,
        cuboid_3d: {
            frame_id: frame?.frameId ?? '',
            px: box.center[0],
            py: box.center[1],
            pz: box.center[2],
            qx: 0,
            qy: 0,
            qz: 0,
            qw: 1,
            sx: box.size[0],
            sy: box.size[1],
            sz: box.size[2]
        }
    };
}

/** Creates point-cloud cuboids using the last selected annotation class when available. */
export function useCreateCuboidAnnotation({
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

    async function selectAnnotationLabel(collectionId: string): Promise<string | null> {
        const stored = get(lastAnnotationLabel)[collectionId] ?? null;
        if (stored) return stored;
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

    async function saveCuboid(
        box: CuboidBox,
        sampleId: string,
        labelId: string,
        frame: SceneFrame | null
    ): Promise<string> {
        const input = buildCuboidInput({ frame, box, labelId, sampleId });
        const annotation = await createAnnotation(input);
        toast.success('Annotation created successfully');
        return annotation.sample_id;
    }

    async function handleCreateCuboid(
        placement: CuboidPlacement,
        onCreated: (annotationId: string) => void | Promise<void>
    ): Promise<void> {
        const collectionId = getCollectionId();
        const sampleId = getTickSampleId();
        const capturedFrame = getSceneFrame();
        if (!collectionId || !sampleId) return;
        const box =
            placement.kind === 'box'
                ? placement.box
                : getDefaultCuboidBox(placement.position, capturedFrame?.bounds ?? ZERO_BOUNDS);
        const labelName = await selectAnnotationLabel(collectionId);
        if (!labelName) return;
        // Cancel if the active tick changed while the class dialog was open.
        if (getTickSampleId() !== sampleId) return;
        const labelId = await findOrCreateLabelId(collectionId, labelName);
        if (!labelId) return;
        // Cancel if the active sample or collection changed while finding/creating the label.
        if (getTickSampleId() !== sampleId || getCollectionId() !== collectionId) return;
        let annotationId: string;
        try {
            annotationId = await saveCuboid(box, sampleId, labelId, capturedFrame);
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
