import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import { useCreateAnnotation } from '$lib/hooks/useCreateAnnotation/useCreateAnnotation';
import { useCreateLabel } from '$lib/hooks/useCreateLabel/useCreateLabel';
import { addAnnotationCreateToUndoStack } from '$lib/services/addAnnotationCreateToUndoStack';
import type { BoundingBox } from '$lib/types';
import { useDeleteAnnotation } from './useDeleteAnnotation/useDeleteAnnotation';
import { useGlobalStorage } from './useGlobalStorage';

export function useCreateSegmentationMask({
    collectionId,
    datasetId,
    sampleId,
    refetch
}: {
    collectionId: string;
    datasetId: string;
    sampleId: string;
    refetch: () => void;
}) {
    const { createLabel } = useCreateLabel({ collectionId });
    const { createAnnotation } = useCreateAnnotation({ collectionId });
    const { deleteAnnotation } = useDeleteAnnotation({ collectionId });
    const { addReversibleAction } = useGlobalStorage();
    const {
        context: annotationLabelContext,
        setAnnotationLabel,
        setAnnotationId,
        setLastCreatedAnnotationId,
        setAnnotationType
    } = useAnnotationLabelContext();

    const createSegmentationMask = async ({
        labelName,
        bbox,
        rle,
        labels,
        onUndo
    }: {
        labelName: string;
        bbox: BoundingBox;
        rle: number[];
        labels: { annotation_label_id?: string; annotation_label_name?: string }[];
        onUndo: () => Promise<void>;
    }) => {
        let label = labels.find((l) => l.annotation_label_name === labelName);

        if (!label) {
            label = await createLabel({
                dataset_id: datasetId,
                annotation_label_name: labelName
            });
        }

        const newAnnotation = await createAnnotation({
            parent_sample_id: sampleId,
            annotation_type: 'segmentation_mask',
            x: bbox.x,
            y: bbox.y,
            width: bbox.width,
            height: bbox.height,
            segmentation_mask: rle,
            annotation_label_id: label.annotation_label_id!,
            annotation_collection_name: annotationLabelContext.annotationSource ?? undefined
        });

        console.log('create segmentaiton');

        addAnnotationCreateToUndoStack({
            annotation: newAnnotation,
            addReversibleAction,
            deleteAnnotation,
            refetch,
            onUndo
        });

        setAnnotationType('segmentation_mask');
        setAnnotationLabel(label.annotation_label_name!);
        setAnnotationId(newAnnotation.sample_id);
        setLastCreatedAnnotationId(newAnnotation.sample_id);

        refetch();
    };

    return { createSegmentationMask };
}
