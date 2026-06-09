import type { AnnotationUpdateInput, AnnotationView } from '$lib/api/lightly_studio_local';
import { useAnnotationLabelContext } from '$lib/contexts/SampleDetailsAnnotation.svelte';
import { addAnnotationUpdateToUndoStack } from '$lib/services/addAnnotationUpdateToUndoStack';
import type { BoundingBox } from '$lib/types';
import { useGlobalStorage } from './useGlobalStorage';

export function useUpdateSegmentationMask({
    collectionId,
    refetch
}: {
    collectionId: string;
    refetch: () => void;
}) {
    const { addReversibleAction } = useGlobalStorage();
    const { setAnnotationType } = useAnnotationLabelContext();

    const updateSegmentationMask = async ({
        annotation,
        bbox,
        rle,
        updateAnnotation,
        onUndo
    }: {
        annotation: AnnotationView;
        bbox: BoundingBox;
        rle: number[];
        updateAnnotation: (input: AnnotationUpdateInput) => Promise<void>;
        onUndo: () => Promise<void>;
    }) => {
        try {
            await updateAnnotation({
                annotation_id: annotation.sample_id!,
                collection_id: collectionId,
                bounding_box: bbox,
                segmentation_mask: rle
            });

            setAnnotationType('segmentation_mask');
            refetch();

            addAnnotationUpdateToUndoStack({
                annotation,
                collection_id: collectionId,
                addReversibleAction,
                updateAnnotation,
                onUndo: async () => {
                    await onUndo();
                    refetch();
                }
            });
        } catch (error) {
            console.error('Failed to update annotation:', (error as Error).message);
        }
    };

    return { updateSegmentationMask };
}
