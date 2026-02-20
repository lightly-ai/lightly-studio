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
import { useUpdateAnnotationsMutation } from './useUpdateAnnotationsMutation/useUpdateAnnotationsMutation';
import { applySegmentationMaskConstraints } from '$lib/utils/segmentationOverlap';

export function useInstanceSegmentationBrush({
    collectionId,
    sampleId,
    sample,
    annotations = [],
    segmentationMode = 'instance',
    refetch,
    onAnnotationCreated
}: {
    collectionId: string;
    sampleId: string;
    sample: { width: number; height: number };
    annotations?: AnnotationView[];
    segmentationMode?: 'instance' | 'semantic';
    refetch: () => void;
    onAnnotationCreated?: () => void;
}) {
    const { createLabel } = useCreateLabel({ collectionId });
    const { createAnnotation } = useCreateAnnotation({ collectionId });
    const { addReversibleAction } = useGlobalStorage();
    const { deleteAnnotation } = useDeleteAnnotation({
        collectionId
    });
    const {
        context: annotationLabelContext,
        setIsDrawing,
        setAnnotationLabel,
        setLastCreatedAnnotationId,
        setAnnotationId,
        setAnnotationType
    } = useAnnotationLabelContext();
    const { updateAnnotations } = useUpdateAnnotationsMutation({ collectionId });

    const finishBrush = async (
        workingMask: Uint8Array | null,
        selectedAnnotation: AnnotationView | null,
        labels: {
            annotation_label_id?: string;
            annotation_label_name?: string;
        }[],
        updateAnnotation?: (input: AnnotationUpdateInput) => Promise<void>,
        lockedAnnotationIds?: Set<string>
    ) => {
        if (!annotationLabelContext.isDrawing || !workingMask) {
            return;
        }

        setIsDrawing(false);

        await applySegmentationMaskConstraints({
            workingMask,
            skipId: selectedAnnotation?.sample_id,
            lockedAnnotationIds,
            annotations,
            segmentationMode,
            sample,
            collectionId,
            updateAnnotations
        });

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
            if (lockedAnnotationIds?.has(selectedAnnotation.sample_id)) {
                toast.error('This annotation is locked');
                return;
            }
            try {
                if (!updateAnnotation) return;
                await updateAnnotation({
                    annotation_id: selectedAnnotation.sample_id!,
                    collection_id: collectionId,
                    bounding_box: bbox,
                    segmentation_mask: rle
                });

                setAnnotationType(
                    segmentationMode === 'semantic'
                        ? 'semantic_segmentation'
                        : 'instance_segmentation'
                );
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
            ) ?? labels?.find((l) => l.annotation_label_name === 'DEFAULT');

        if (!label) {
            label = await createLabel({
                dataset_id: collectionId,
                annotation_label_name: 'DEFAULT'
            });
        }

        const newAnnotation = await createAnnotation({
            parent_sample_id: sampleId,
            annotation_type:
                segmentationMode === 'semantic' ? 'semantic_segmentation' : 'instance_segmentation',
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

        setAnnotationType(
            segmentationMode === 'semantic' ? 'semantic_segmentation' : 'instance_segmentation'
        );
        setAnnotationLabel(label.annotation_label_name!);
        setAnnotationId(newAnnotation.sample_id);
        setLastCreatedAnnotationId(newAnnotation.sample_id);

        refetch();
        onAnnotationCreated?.();
    };

    return { finishBrush };
}
