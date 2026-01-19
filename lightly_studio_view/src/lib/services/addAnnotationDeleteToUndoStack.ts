import type {
    AnnotationCreateInput,
    AnnotationLabelTable,
    AnnotationView,
    CreateAnnotationResponse
} from '$lib/api/lightly_studio_local';
import type { ReversibleAction } from '$lib/hooks/useReversibleActions';

export const ANNOTATION_DELETE_GROUP_ID = 'annotation-delete';

export const addAnnotationDeleteToUndoStack = ({
    annotation,
    labels,
    addReversibleAction,
    createAnnotation,
    refetch
}: {
    annotation: AnnotationView;
    labels: AnnotationLabelTable[];
    addReversibleAction: (action: ReversibleAction) => void;
    createAnnotation: (input: AnnotationCreateInput) => Promise<CreateAnnotationResponse>;
    refetch: () => void;
}) => {
    const labelName = annotation.annotation_label.annotation_label_name;
    const label = labels.find((l) => l.annotation_label_name === labelName);
    if (!label?.annotation_label_id) return;

    const annotationInput: AnnotationCreateInput = {
        parent_sample_id: annotation.parent_sample_id,
        annotation_type: annotation.annotation_type,
        annotation_label_id: label.annotation_label_id,
        x: annotation.object_detection_details?.x ?? annotation.segmentation_details?.x,
        y: annotation.object_detection_details?.y ?? annotation.segmentation_details?.y,
        width: annotation.object_detection_details?.width ?? annotation.segmentation_details?.width,
        height:
            annotation.object_detection_details?.height ?? annotation.segmentation_details?.height,
        segmentation_mask: annotation.segmentation_details?.segmentation_mask
    };

    const execute = async () => {
        await createAnnotation(annotationInput);
        refetch();
    };

    addReversibleAction({
        id: `annotation-delete-${annotation.sample_id}-${Date.now()}`,
        description: `Undo delete annotation`,
        execute,
        timestamp: new Date(),
        groupId: ANNOTATION_DELETE_GROUP_ID
    });
};
