import type { AnnotationUpdateInput, AnnotationView } from '$lib/api/lightly_studio_local';
import { readAnnotationLabels } from '$lib/api/lightly_studio_local/sdk.gen';
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
import { restoreOverriddenSegmentationAnnotationsForUndo } from '$lib/services/restoreOverriddenSegmentationAnnotationsForUndo';

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

    const findMatchingLabel = (
        labels: {
            annotation_label_id?: string;
            annotation_label_name?: string;
        }[]
    ) =>
        labels.find((l) => l.annotation_label_name === annotationLabelContext.annotationLabel) ??
        labels.find((l) => l.annotation_label_name === 'DEFAULT') ??
        null;

    const resolveAnnotationLabel = async (
        labels: {
            annotation_label_id?: string;
            annotation_label_name?: string;
        }[]
    ) => {
        const existingLabel = findMatchingLabel(labels);
        if (existingLabel) {
            return existingLabel;
        }

        const { data: fetchedLabels } = await readAnnotationLabels({
            path: { collection_id: collectionId }
        });
        const fetchedLabel = findMatchingLabel(fetchedLabels ?? []);
        if (fetchedLabel) {
            return fetchedLabel;
        }

        try {
            return await createLabel({
                root_collection_id: collectionId,
                annotation_label_name: 'DEFAULT'
            });
        } catch (error) {
            const { data: refreshedLabels } = await readAnnotationLabels({
                path: { collection_id: collectionId }
            });
            const refreshedLabel = findMatchingLabel(refreshedLabels ?? []);
            if (refreshedLabel) {
                return refreshedLabel;
            }

            throw error;
        }
    };

    const finishBrush = async (
        workingMask: Uint8Array | null,
        selectedAnnotation: AnnotationView | null,
        labels: {
            annotation_label_id?: string;
            annotation_label_name?: string;
        }[],
        updateAnnotation?: (input: AnnotationUpdateInput) => Promise<void>,
        lockedAnnotationIds?: Set<string>,
        options?: {
            deferDrawingReset?: boolean;
            skipImageRefetch?: boolean;
            refreshAnnotations?: (annotation: AnnotationView) => void | Promise<void>;
        }
    ): Promise<AnnotationView | null> => {
        if (!annotationLabelContext.isDrawing || !workingMask) {
            return null;
        }

        const deferDrawingReset = options?.deferDrawingReset ?? false;
        const skipImageRefetch = options?.skipImageRefetch ?? false;
        const refreshAnnotations = options?.refreshAnnotations;
        if (!deferDrawingReset) {
            setIsDrawing(false);
        }

        try {
            if (
                selectedAnnotation?.sample_id &&
                lockedAnnotationIds?.has(selectedAnnotation.sample_id)
            ) {
                // Prevent any overlap updates or mask mutations when the selected annotation is locked.
                refetch();
                toast.error('This annotation is locked');
                return null;
            }

            const overriddenAnnotations = await applySegmentationMaskConstraints({
                workingMask,
                skipId: selectedAnnotation?.sample_id,
                lockedAnnotationIds,
                annotations,
                segmentationMode,
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
                return null;
            }

            const rle = encodeBinaryMaskToRLE(workingMask);
            if (selectedAnnotation) {
                try {
                    if (!updateAnnotation) return null;
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
                    const updatedAnnotation: AnnotationView = {
                        ...selectedAnnotation,
                        segmentation_details: {
                            x: bbox.x,
                            y: bbox.y,
                            width: bbox.width,
                            height: bbox.height,
                            segmentation_mask: rle
                        }
                    };

                    if (!skipImageRefetch) {
                        refetch();
                    }
                    await refreshAnnotations?.(updatedAnnotation);

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

                    return updatedAnnotation;
                } catch (error) {
                    console.error('Failed to update annotation:', (error as Error).message);
                    return null;
                }
            }

            const label = await resolveAnnotationLabel(labels ?? []);

            const newAnnotation = await createAnnotation({
                parent_sample_id: sampleId,
                annotation_type:
                    segmentationMode === 'semantic'
                        ? 'semantic_segmentation'
                        : 'instance_segmentation',
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
                refetch,
                onUndo: restoreOverriddenAnnotations
            });

            setAnnotationType(
                segmentationMode === 'semantic'
                    ? 'semantic_segmentation'
                    : 'instance_segmentation'
            );
            setAnnotationLabel(label.annotation_label_name!);
            setAnnotationId(newAnnotation.sample_id);
            setLastCreatedAnnotationId(newAnnotation.sample_id);

            if (!skipImageRefetch) {
                refetch();
            }
            await refreshAnnotations?.(newAnnotation);
            onAnnotationCreated?.();
            return newAnnotation;
        } finally {
            if (deferDrawingReset) {
                setIsDrawing(false);
            }
        }
    };

    return { finishBrush };
}
