import type { AnnotationUpdateInput, AnnotationView } from '$lib/api/lightly_studio_local';
import {
    computeBoundingBoxFromMask,
    decodeRLEToBinaryMask,
    encodeBinaryMaskToRLE
} from '$lib/components/SampleAnnotation/utils';

type CommonParams = {
    lockedAnnotationIds?: Set<string>;
    annotations: AnnotationView[] | undefined;
    sample: { width: number; height: number };
};

type RemoveOverlapParams = CommonParams & {
    newMask: Uint8Array;
    skipId?: string;
    segmentationMode: 'instance' | 'semantic';
    collectionId: string;
    updateAnnotations: (updates: AnnotationUpdateInput[]) => Promise<unknown>;
};

/**
 * Clears pixels from other semantic masks that overlap the new mask,
 * respecting locked annotations and the current segmentation mode.
 */
export const removeOverlapFromOtherSemanticAnnotations = async ({
    newMask,
    skipId,
    lockedAnnotationIds,
    annotations,
    segmentationMode,
    sample,
    collectionId,
    updateAnnotations
}: RemoveOverlapParams) => {
    if (segmentationMode !== 'semantic') return;
    if (!annotations?.length) return;

    const updates: AnnotationUpdateInput[] = [];

    annotations
        .filter((ann) => {
            const isSemantic = ann.annotation_type === 'semantic_segmentation';
            const hasMask = ann.segmentation_details?.segmentation_mask;
            const isSame = ann.sample_id === skipId;
            const isLocked = lockedAnnotationIds?.has(ann.sample_id);
            return isSemantic && hasMask && !isSame && !isLocked;
        })
        .forEach((ann) => {
            const otherMask = decodeRLEToBinaryMask(
                ann.segmentation_details!.segmentation_mask!,
                sample.width,
                sample.height
            );

            let changed = false;
            for (let i = 0; i < newMask.length; i++) {
                if (newMask[i] === 1 && otherMask[i] === 1) {
                    otherMask[i] = 0;
                    changed = true;
                }
            }

            if (!changed) return;

            const bbox = computeBoundingBoxFromMask(otherMask, sample.width, sample.height);
            updates.push({
                annotation_id: ann.sample_id,
                collection_id: collectionId,
                segmentation_mask: encodeBinaryMaskToRLE(otherMask),
                bounding_box: bbox ?? null
            });
        });

    if (updates.length) {
        await updateAnnotations(updates);
    }
};

type StripLockedParams = CommonParams & { mask: Uint8Array };

/**
 * Removes pixels in the working mask that collide with locked segmentation masks.
 */
export const stripLockedPixels = ({
    mask,
    lockedAnnotationIds,
    annotations,
    sample
}: StripLockedParams) => {
    if (!lockedAnnotationIds?.size || !annotations?.length) return;

    annotations
        .filter(
            (ann) =>
                lockedAnnotationIds.has(ann.sample_id) &&
                ann.segmentation_details?.segmentation_mask
        )
        .forEach((ann) => {
            const lockedMask = decodeRLEToBinaryMask(
                ann.segmentation_details!.segmentation_mask!,
                sample.width,
                sample.height
            );

            for (let i = 0; i < mask.length; i++) {
                if (lockedMask[i] === 1 && mask[i] === 1) {
                    mask[i] = 0;
                }
            }
        });
};

type ApplyMaskConstraintsParams = RemoveOverlapParams & { workingMask: Uint8Array };

export const applySegmentationMaskConstraints = async ({
    workingMask,
    ...rest
}: ApplyMaskConstraintsParams) => {
    // Preserve the drawn mask for overlap removal; locked stripping mutates workingMask.
    const maskForOverlap = workingMask.slice();

    stripLockedPixels({
        mask: workingMask,
        lockedAnnotationIds: rest.lockedAnnotationIds,
        annotations: rest.annotations,
        sample: rest.sample
    });

    await removeOverlapFromOtherSemanticAnnotations({
        newMask: maskForOverlap,
        ...rest
    });
};
