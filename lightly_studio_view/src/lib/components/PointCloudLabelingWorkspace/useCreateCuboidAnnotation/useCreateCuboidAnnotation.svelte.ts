import {
    useAnnotationLabels,
    useCreateAnnotation,
    useCreateLabel,
    useGlobalStorage,
    useSelectClassDialog
} from '$lib/hooks';
import { get } from 'svelte/store';
import { toast } from 'svelte-sonner';
import type { AnnotationCreateInput } from '$lib/api/lightly_studio_local';
import type { Bounds3, Vector3 } from '$lib/components/PointCloudLabelingWorkspace/domain';

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
    groundPosition: Vector3;
    labelId: string;
    sampleId: string;
}

interface UseCreateCuboidAnnotationReturn {
    handleCreateCuboid: (
        groundPosition: Vector3,
        onCreated: (annotationId: string) => void | Promise<void>
    ) => Promise<void>;
    showSelectClassDialog: ReturnType<typeof useSelectClassDialog>['open'];
    handleClassSelected: ReturnType<typeof useSelectClassDialog>['handleConfirm'];
    handleClassDialogCancel: ReturnType<typeof useSelectClassDialog>['handleCancel'];
    labels: ReturnType<typeof useAnnotationLabels>;
}

const ZERO_BOUNDS: Bounds3 = { min: [0, 0, 0], max: [0, 0, 0] };

function computeDefaultCuboidSize(bounds: Bounds3): number {
    const diagonal = Math.hypot(
        bounds.max[0] - bounds.min[0],
        bounds.max[1] - bounds.min[1],
        bounds.max[2] - bounds.min[2]
    );
    return Math.max(diagonal * 0.02, 0.1);
}

function buildCuboidInput({
    frame,
    groundPosition,
    labelId,
    sampleId
}: CreateCuboidParams): AnnotationCreateInput {
    const size = computeDefaultCuboidSize(frame?.bounds ?? ZERO_BOUNDS);
    return {
        parent_sample_id: sampleId,
        annotation_type: 'cuboid_3d',
        annotation_label_id: labelId,
        cuboid_3d: {
            frame_id: frame?.frameId ?? '',
            px: groundPosition[0],
            py: groundPosition[1],
            pz: groundPosition[2] + size / 2,
            qx: 0,
            qy: 0,
            qz: 0,
            qw: 1,
            sx: size,
            sy: size,
            sz: size
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
    let annotationLabel = get(lastAnnotationLabel)[getCollectionId() ?? ''] ?? null;

    async function selectAnnotationLabel(collectionId: string): Promise<string | null> {
        if (annotationLabel) return annotationLabel;
        const selection = await requestLabel();
        if (!selection?.label) return null;
        annotationLabel = selection.label;
        updateLastAnnotationLabel(collectionId, annotationLabel);
        return annotationLabel;
    }

    async function findOrCreateLabelId(labelName: string): Promise<string | null> {
        const existingLabel = labels.data?.find(
            (label) => label.annotation_label_name === labelName
        );
        if (existingLabel?.annotation_label_id) return existingLabel.annotation_label_id;
        try {
            const label = await createLabel({
                dataset_id: getDatasetId(),
                annotation_label_name: labelName
            });
            return label.annotation_label_id ?? null;
        } catch {
            toast.error('Failed to create annotation class. Please try again.');
            return null;
        }
    }

    async function saveCuboid(
        groundPosition: Vector3,
        sampleId: string,
        labelId: string
    ): Promise<string> {
        const input = buildCuboidInput({
            frame: getSceneFrame(),
            groundPosition,
            labelId,
            sampleId
        });
        const annotation = await createAnnotation(input);
        toast.success('Annotation created successfully');
        return annotation.sample_id;
    }

    async function handleCreateCuboid(
        groundPosition: Vector3,
        onCreated: (annotationId: string) => void | Promise<void>
    ): Promise<void> {
        const collectionId = getCollectionId();
        const sampleId = getTickSampleId();
        if (!collectionId || !sampleId) return;
        const labelName = await selectAnnotationLabel(collectionId);
        if (!labelName) return;
        const labelId = await findOrCreateLabelId(labelName);
        if (!labelId) return;
        let annotationId: string;
        try {
            annotationId = await saveCuboid(groundPosition, sampleId, labelId);
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
