import type { AnnotationUpdateInput, AnnotationView } from '$lib/api/lightly_studio_local';
import {
    computeBoundingBoxFromMask,
    encodeBinaryMaskToRLE
} from '$lib/components/SampleAnnotation/utils';
import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import { useCreateAnnotation } from '$lib/hooks/useCreateAnnotation/useCreateAnnotation';
import { restoreOverriddenSegmentationAnnotationsForUndo } from '$lib/services/restoreOverriddenSegmentationAnnotationsForUndo';
import { applySegmentationMaskConstraints } from '$lib/utils/segmentationOverlap';
import { toast } from 'svelte-sonner';
import { useCreateSegmentationMask } from './useCreateSegmentationMask';
import { useResolveAnnotationLabel } from './useResolveAnnotationLabel';
import { useUpdateAnnotationsMutation } from './useUpdateAnnotationsMutation/useUpdateAnnotationsMutation';
import { useUpdateSegmentationMask } from './useUpdateSegmentationMask';

export function useSegmentationMaskBrush({
    collectionId,
    datasetId,
    sampleId,
    sample,
    annotations = [],
    refetch,
    onAnnotationCreated,
    requestLabel
}: {
    collectionId: string;
    datasetId: string;
    sampleId: string;
    sample: { width: number; height: number };
    annotations?: AnnotationView[];
    refetch: () => void;
    onAnnotationCreated?: () => void;
    /** Called when no label is currently selected. Should show a class-picker and resolve with
     *  the chosen class, or null if the user cancelled. */
    requestLabel?: () => Promise<{ label: string } | null>;
}) {
    const { context: annotationLabelContext, setIsDrawing } = useAnnotationLabelContext();
    const { updateAnnotations } = useUpdateAnnotationsMutation({ collectionId });
    const { createAnnotation } = useCreateAnnotation({ collectionId });
    const { resolveAnnotationLabel } = useResolveAnnotationLabel({ collectionId, requestLabel });
    const { updateSegmentationMask } = useUpdateSegmentationMask({ collectionId, refetch });
    const { createSegmentationMask } = useCreateSegmentationMask({
        collectionId,
        datasetId,
        sampleId,
        refetch
    });

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

        let labelName = annotationLabelContext.annotationLabel;
        if (!selectedAnnotation) {
            labelName = await resolveAnnotationLabel();
            if (!labelName) return;
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

        const bbox = computeBoundingBoxFromMask(workingMask, sample.width, sample.height);
        if (!bbox) {
            toast.error('Invalid segmentation mask');
            return;
        }
        const rle = encodeBinaryMaskToRLE(workingMask);

        if (selectedAnnotation) {
            if (!updateAnnotation) return;
            await updateSegmentationMask({
                annotation: selectedAnnotation,
                bbox,
                rle,
                updateAnnotation,
                onUndo: restoreOverriddenAnnotations
            });
            return;
        }

        await createSegmentationMask({
            labelName: labelName!,
            bbox,
            rle,
            labels,
            onUndo: restoreOverriddenAnnotations
        });

        onAnnotationCreated?.();
    };

    return { finishBrush };
}
