import type {
    AnnotationCollectionView,
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
    sources,
    addReversibleAction,
    createAnnotation,
    refetch
}: {
    annotation: AnnotationView;
    labels: AnnotationLabelTable[];
    // Sources for the annotation's collection, so undo can recreate it in its original
    // source instead of falling back to the default one. See getSourceName below.
    sources: AnnotationCollectionView[];
    addReversibleAction: (action: ReversibleAction) => void;
    createAnnotation: (input: AnnotationCreateInput) => Promise<CreateAnnotationResponse>;
    refetch: () => void;
}) => {
    const labelName = annotation.annotation_label.annotation_label_name;
    const label = labels.find((l) => l.annotation_label_name === labelName);
    if (!label?.annotation_label_id) return;

    // The backend re-creates the annotation in the default source when
    // annotation_collection_name is omitted, so undo must resolve and pass the
    // original source's name explicitly to restore it there instead.
    const sourceName = sources.find(
        (source) => source.collection_id === annotation.annotation_collection_id
    )?.name;

    const cuboid3d = annotation.cuboid_3d_details;

    const annotationInput: AnnotationCreateInput = {
        parent_sample_id: annotation.parent_sample_id,
        annotation_type: annotation.annotation_type,
        annotation_label_id: label.annotation_label_id,
        annotation_collection_name: sourceName,
        x: annotation.object_detection_details?.x ?? annotation.segmentation_details?.x,
        y: annotation.object_detection_details?.y ?? annotation.segmentation_details?.y,
        width: annotation.object_detection_details?.width ?? annotation.segmentation_details?.width,
        height:
            annotation.object_detection_details?.height ?? annotation.segmentation_details?.height,
        segmentation_mask: annotation.segmentation_details?.segmentation_mask,
        cuboid_3d: cuboid3d
            ? {
                  frame_id: cuboid3d.frame_id,
                  px: cuboid3d.px,
                  py: cuboid3d.py,
                  pz: cuboid3d.pz,
                  qx: cuboid3d.qx,
                  qy: cuboid3d.qy,
                  qz: cuboid3d.qz,
                  qw: cuboid3d.qw,
                  sx: cuboid3d.sx,
                  sy: cuboid3d.sy,
                  sz: cuboid3d.sz
              }
            : undefined
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
