import type { AnnotationUpdateInput, AnnotationView } from '$lib/api/lightly_studio_local';
import {
    computeBoundingBoxFromMask,
    encodeBinaryMaskToRLE
} from '$lib/components/SampleAnnotation/utils';
import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import { useCreateAnnotation } from '$lib/hooks/useCreateAnnotation/useCreateAnnotation';
import { useCreateLabel } from '$lib/hooks/useCreateLabel/useCreateLabel';
import { addAnnotationUpdateToUndoStack } from '$lib/services/addAnnotationUpdateToUndoStack';
import type { BoundingBox } from '$lib/types';
import { toast } from 'svelte-sonner';
import { useGlobalStorage } from './useGlobalStorage';
import { addAnnotationCreateToUndoStack } from '$lib/services/addAnnotationCreateToUndoStack';
import { useDeleteAnnotation } from './useDeleteAnnotation/useDeleteAnnotation';

export function useInstanceSegmentationBrush({
    collectionId,
    sampleId,
    sample,
    refetch
}: {
    collectionId: string;
    sampleId: string;
    sample: { width: number; height: number };
    refetch: () => void;
}) {
    const { createLabel } = useCreateLabel({ collectionId });
    const { createAnnotation } = useCreateAnnotation({ collectionId });
    const annotationLabelContext = useAnnotationLabelContext();
    const { addReversibleAction } = useGlobalStorage();
    const { deleteAnnotation } = useDeleteAnnotation({
        collectionId
    });

    const finishBrush = async (
        workingMask: Uint8Array | null,
        selectedAnnotation: AnnotationView | null,
        labels: {
            annotation_label_id?: string;
            annotation_label_name?: string;
        }[],
        updateAnnotation?: (input: AnnotationUpdateInput) => Promise<void>
    ) => {
        if (!annotationLabelContext.isDrawing || !workingMask) {
            annotationLabelContext.isDrawing = false;
            return;
        }

        annotationLabelContext.isDrawing = false;

        const bbox: BoundingBox | null = computeBoundingBoxFromMask(
            workingMask,
            sample.width,
            sample.height
        );

        if (!bbox) {
            toast.error('Invalid segmentation mask');
            return;
        }

        const rle = encodeBinaryMaskToRLE(workingMask);
        if (selectedAnnotation) {
            try {
                if (!updateAnnotation) return;
                await updateAnnotation({
                    annotation_id: selectedAnnotation.sample_id!,
                    collection_id: collectionId,
                    bounding_box: bbox,
                    segmentation_mask: rle
                });

                refetch();

                addAnnotationUpdateToUndoStack({
                    annotation: selectedAnnotation,
                    collection_id: collectionId,
                    addReversibleAction,
                    updateAnnotation
                });

                return;
            } catch (error) {
                console.error('Failed to update annotation:', (error as Error).message);
                return;
            }
        }

        let label =
            labels?.find(
                (l) => l.annotation_label_name === annotationLabelContext.annotationLabel
            ) ?? labels?.find((l) => l.annotation_label_name === 'default');

        if (!label) {
            label = await createLabel({
                dataset_id: collectionId,
                annotation_label_name: 'default'
            });
        }

        const newAnnotation = await createAnnotation({
            parent_sample_id: sampleId,
            annotation_type: 'instance_segmentation',
            x: bbox.x,
            y: bbox.y,
            width: bbox.width,
            height: bbox.height,
            segmentation_mask: rle,
            annotation_label_id: label.annotation_label_id!
        });

        addAnnotationCreateToUndoStack({
            annotation: newAnnotation,
            addReversibleAction,
            deleteAnnotation,
            refetch
        });

        annotationLabelContext.annotationLabel = label.annotation_label_name;
        annotationLabelContext.annotationId = newAnnotation.sample_id;
        annotationLabelContext.lastCreatedAnnotationId = newAnnotation.sample_id;

        refetch();
    };

    return { finishBrush };
}
