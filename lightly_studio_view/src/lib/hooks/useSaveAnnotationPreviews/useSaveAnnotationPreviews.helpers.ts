import {
    AnnotationType,
    type AnnotationCreateInput,
    type AnnotationPreview
} from '$lib/api/lightly_studio_local';

export const previewToCreateInput = ({
    preview,
    saveAs
}: {
    preview: AnnotationPreview;
    saveAs: 'mask' | 'box';
}): Omit<AnnotationCreateInput, 'annotation_label_id' | 'parent_sample_id'> =>
    saveAs === 'box'
        ? { annotation_type: AnnotationType.OBJECT_DETECTION, ...preview.bbox }
        : {
              annotation_type: AnnotationType.SEGMENTATION_MASK,
              ...preview.bbox,
              segmentation_mask: preview.segmentation_mask
          };
