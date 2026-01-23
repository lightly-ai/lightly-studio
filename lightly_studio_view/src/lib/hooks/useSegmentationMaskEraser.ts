import type { AnnotationUpdateInput, AnnotationView } from '$lib/api/lightly_studio_local';
import {
    computeBoundingBoxFromMask,
    encodeBinaryMaskToRLE
} from '$lib/components/SampleAnnotation/utils';
import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import type { BoundingBox } from '$lib/types';
import { toast } from 'svelte-sonner';
import { useGlobalStorage } from './useGlobalStorage';
import { addAnnotationUpdateToUndoStack } from '$lib/services/addAnnotationUpdateToUndoStack';

export function useSegmentationMaskEraser({
    collectionId,
    sample,
    refetch
}: {
    collectionId: string;
    sample: {
        width: number;
        height: number;
    };
    refetch?: () => void;
}) {
    const { addReversibleAction } = useGlobalStorage();
    const { context: annotationLabelContext } = useAnnotationLabelContext();

    const finishErase = async (
        workingMask: Uint8Array | null,
        selectedAnnotation: AnnotationView | null,
        update?: (input: AnnotationUpdateInput) => Promise<void>,
        remove?: () => Promise<void>
    ) => {
        if (!annotationLabelContext.isDrawing || !workingMask || !selectedAnnotation) {
            annotationLabelContext.isDrawing = false;
            return;
        }

        const bbox: BoundingBox | null = computeBoundingBoxFromMask(
            workingMask,
            sample.width,
            sample.height
        );

        if (!bbox) {
            try {
                await remove?.();
                refetch?.();
            } catch (error) {
                toast.error('Failed to delete annotation. Please try again.');
                console.error('Error deleting annotation:', error);
            }
            return;
        }

        const rle = encodeBinaryMaskToRLE(workingMask);

        try {
            if (!update) return;

            await update({
                annotation_id: selectedAnnotation?.sample_id,
                collection_id: collectionId,
                bounding_box: bbox,
                segmentation_mask: rle
            });

            addAnnotationUpdateToUndoStack({
                annotation: selectedAnnotation,
                collection_id: collectionId,
                addReversibleAction,
                updateAnnotation: update
            });

            refetch?.();
        } catch (err) {
            console.error(err);
            toast.error('Failed to update segmentation');
        }
    };

    return { finishErase };
}
