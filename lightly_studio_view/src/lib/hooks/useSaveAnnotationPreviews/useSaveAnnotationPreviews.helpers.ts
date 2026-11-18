import {
    AnnotationType,
    type AnnotationCreateInput,
    type AnnotationPreview
} from '$lib/api/lightly_studio_local';

interface SavablePreview {
    bbox: AnnotationPreview['bbox'];
    // Null for a box-only preview, e.g. from an object detection model.
    segmentation_mask: AnnotationPreview['segmentation_mask'] | null;
}

// A preview without a mask saves as a box, also when saveAs is 'mask'.
export const previewToCreateInput = ({
    preview,
    saveAs
}: {
    preview: SavablePreview;
    saveAs: 'mask' | 'box';
}): Omit<AnnotationCreateInput, 'annotation_label_id' | 'parent_sample_id'> =>
    saveAs === 'box' || preview.segmentation_mask === null
        ? { annotation_type: AnnotationType.OBJECT_DETECTION, ...preview.bbox }
        : {
              annotation_type: AnnotationType.SEGMENTATION_MASK,
              ...preview.bbox,
              segmentation_mask: preview.segmentation_mask
          };
