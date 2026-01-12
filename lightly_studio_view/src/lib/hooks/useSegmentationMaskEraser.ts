import type { AnnotationUpdateInput } from '$lib/api/lightly_studio_local';
import {
    computeBoundingBoxFromMask,
    encodeBinaryMaskToRLE
} from '$lib/components/SampleAnnotation/utils';
import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import type { BoundingBox } from '$lib/types';
import { toast } from 'svelte-sonner';

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
    refetch: () => void;
}) {
    const annotationLabelContext = useAnnotationLabelContext();

    const finishErase = async (
        workingMask: Uint8Array | null,
        update?: (input: AnnotationUpdateInput) => Promise<void>,
        remove?: () => Promise<void>
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
            try {
                await remove?.();
                refetch();
            } catch (error) {
                toast.error('Failed to delete annotation. Please try again.');
                console.error('Error deleting annotation:', error);
            }
            return;
        }

        const rle = encodeBinaryMaskToRLE(workingMask);

        try {
            await update?.({
                annotation_id: annotationLabelContext.annotationId!,
                collection_id: collectionId,
                bounding_box: bbox,
                segmentation_mask: rle
            });
            refetch();
        } catch (err) {
            console.error(err);
            toast.error('Failed to update segmentation');
        }
    };

    return { finishErase };
}
