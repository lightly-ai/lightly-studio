import type {
    AnnotationCollectionView,
    AnnotationCreateInput,
    AnnotationLabelTable,
    AnnotationView,
    CreateAnnotationResponse
} from '$lib/api/lightly_studio_local';
import type { ReversibleAction } from '$lib/hooks/useReversibleActions';

export const ANNOTATION_DELETE_GROUP_ID = 'annotation-delete';

// The backend re-creates the annotation in the default source when
// annotation_collection_name is omitted, so undo must resolve and pass the
// original source's name explicitly to restore it there instead.
const getSourceName = (
    annotation: AnnotationView,
    sources: AnnotationCollectionView[]
): string | undefined =>
    sources.find((source) => source.collection_id === annotation.annotation_collection_id)?.name;

const getRectangle = ({ object_detection_details, segmentation_details }: AnnotationView) => {
    const rectangle = object_detection_details ?? segmentation_details;
    return {
        x: rectangle?.x,
        y: rectangle?.y,
        width: rectangle?.width,
        height: rectangle?.height
    };
};

const buildRestoreInput = (
    annotation: AnnotationView,
    annotationLabelId: string,
    sources: AnnotationCollectionView[]
): AnnotationCreateInput => ({
    parent_sample_id: annotation.parent_sample_id,
    annotation_type: annotation.annotation_type,
    annotation_label_id: annotationLabelId,
    annotation_collection_name: getSourceName(annotation, sources),
    ...getRectangle(annotation),
    segmentation_mask: annotation.segmentation_details?.segmentation_mask,
    polygons: annotation.polygon_details?.polygons,
    cuboid_3d: annotation.cuboid_3d_details,
    object_track_id: annotation.object_track_id
});

export const addAnnotationDeleteToUndoStack = ({
    annotation,
    labels,
    sources,
    addReversibleAction,
    createAnnotation,
    refetch,
    onRestored
}: {
    annotation: AnnotationView;
    labels: AnnotationLabelTable[];
    // Sources for the annotation's collection, so undo can recreate it in its original
    // source instead of falling back to the default one. See getSourceName.
    sources: AnnotationCollectionView[];
    addReversibleAction: (action: ReversibleAction) => void;
    createAnnotation: (input: AnnotationCreateInput) => Promise<CreateAnnotationResponse>;
    /** The undo waits for a returned promise, so it is complete when the view shows the annotation. */
    refetch: () => unknown;
    /** Receives the re-created annotation. It has a new ID. */
    onRestored?: (annotation: AnnotationView) => void;
}) => {
    const labelName = annotation.annotation_label.annotation_label_name;
    const label = labels.find((l) => l.annotation_label_name === labelName);
    if (!label?.annotation_label_id) return;

    const annotationInput = buildRestoreInput(annotation, label.annotation_label_id, sources);

    const execute = async () => {
        const restored = await createAnnotation(annotationInput);
        onRestored?.(restored);
        // The annotation exists again, so a failed refresh must not keep the undo in the history.
        await Promise.allSettled([refetch()]);
    };

    addReversibleAction({
        id: `annotation-delete-${annotation.sample_id}-${Date.now()}`,
        description: `Undo delete annotation`,
        execute,
        timestamp: new Date(),
        groupId: ANNOTATION_DELETE_GROUP_ID
    });
};
