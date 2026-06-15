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
import { useUpdateAnnotationsMutation } from './useUpdateAnnotationsMutation/useUpdateAnnotationsMutation';
import { applySegmentationMaskConstraints } from '$lib/utils/segmentationOverlap';
import { restoreOverriddenSegmentationAnnotationsForUndo } from '$lib/services/restoreOverriddenSegmentationAnnotationsForUndo';

export function useSegmentationMaskBrush({
    collectionId,
    datasetId,
    sampleId,
    sample,
    annotations = [],
    refetch,
    deleteAnnotation,
    onAnnotationCreated,
    requestLabel
}: {
    collectionId: string;
    datasetId: string;
    sampleId: string;
    sample: { width: number; height: number };
    annotations?: AnnotationView[];
    refetch: () => void;
    /** Must be a stable reference (not recreated on re-renders) to ensure undo closures
     *  call the live mutation rather than a disposed one. */
    deleteAnnotation: (annotationId: string) => Promise<void>;
    onAnnotationCreated?: () => void;
    /** Called when no label is currently selected. Should show a class-picker and resolve with
     *  the chosen class, or null if the user cancelled. */
    requestLabel?: () => Promise<{ label: string } | null>;
}) {
    const { createLabel } = useCreateLabel({ collectionId });
    const { createAnnotation } = useCreateAnnotation({ collectionId });
    const { addReversibleAction, updateLastAnnotationLabel } = useGlobalStorage();
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

        if (
            selectedAnnotation?.sample_id &&
            lockedAnnotationIds?.has(selectedAnnotation.sample_id)
        ) {
            // Prevent any overlap updates or mask mutations when the selected annotation is locked.
            refetch();
            toast.error('This annotation is locked');
            return;
        }

        let annotationLabelName = annotationLabelContext.annotationLabel;
        if (!selectedAnnotation && !annotationLabelName) {
            const result = requestLabel ? await requestLabel() : null;
            if (!result?.label) {
                toast.error('Please select a class before creating an annotation');
                return;
            }
            annotationLabelName = result.label;
            setAnnotationLabel(annotationLabelName);
            updateLastAnnotationLabel(collectionId, annotationLabelName);
        }

        const overriddenAnnotations = await applySegmentationMaskConstraints({
            workingMask,
            skipId: selectedAnnotation?.sample_id,
            lockedAnnotationIds,
            annotations,
            sample,
            collectionId,
            updateAnnotations
        });

        const restoreOverriddenAnnotations = async () => {
            await restoreOverriddenSegmentationAnnotationsForUndo({
                collectionId,
                overriddenAnnotations,
                labels,
                updateAnnotations,
                createAnnotation
            });
        };

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

                setAnnotationType('segmentation_mask');
                refetch();

                addAnnotationUpdateToUndoStack({
                    annotation: selectedAnnotation,
                    collection_id: collectionId,
                    addReversibleAction,
                    updateAnnotation,
                    onUndo: async () => {
                        await restoreOverriddenAnnotations();
                        refetch();
                    }
                });

                return;
            } catch (error) {
                console.error('Failed to update annotation:', (error as Error).message);
                return;
            }
        }

        let label = labels?.find((l) => l.annotation_label_name === annotationLabelName);

        if (!label) {
            label = await createLabel({
                dataset_id: datasetId,
                annotation_label_name: annotationLabelName!
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

        addAnnotationCreateToUndoStack({
            annotation: newAnnotation,
            addReversibleAction,
            deleteAnnotation,
            refetch,
            onUndo: restoreOverriddenAnnotations,
            onDelete: () => {
                if (annotationLabelContext.annotationId === newAnnotation.sample_id) {
                    setAnnotationId(null);
                }
            }
        });

        setAnnotationType('segmentation_mask');
        setAnnotationLabel(label.annotation_label_name!);
        setAnnotationId(newAnnotation.sample_id);
        setLastCreatedAnnotationId(newAnnotation.sample_id);

        refetch();
        onAnnotationCreated?.();
    };

    return { finishBrush };
}
