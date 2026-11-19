import {
    AnnotationType,
    type AnnotationCreateInput,
    type ModelAnnotationPreview
} from '$lib/api/lightly_studio_local';

// A preview without a mask, e.g. from an object detection model, saves as a box, also when
// saveAs is 'mask'.
export const previewToCreateInput = ({
    preview,
    saveAs
}: {
    preview: Pick<ModelAnnotationPreview, 'bbox' | 'segmentation_mask'>;
    saveAs: 'mask' | 'box';
}): Omit<AnnotationCreateInput, 'annotation_label_id' | 'parent_sample_id'> =>
    saveAs === 'box' || preview.segmentation_mask === null
        ? { annotation_type: AnnotationType.OBJECT_DETECTION, ...preview.bbox }
        : {
              annotation_type: AnnotationType.SEGMENTATION_MASK,
              ...preview.bbox,
              segmentation_mask: preview.segmentation_mask
          };
