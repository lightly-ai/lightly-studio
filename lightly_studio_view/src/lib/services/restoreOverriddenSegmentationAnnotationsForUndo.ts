import type {
    AnnotationCreateInput,
    AnnotationUpdateInput,
    AnnotationView,
    CreateAnnotationResponse
} from '$lib/api/lightly_studio_local';
import { getBoundingBox } from '$lib/components/SampleAnnotation/utils';

type AnnotationLabelOption = {
    annotation_label_id?: string;
    annotation_label_name?: string;
};

type AnnotationViewWithOptionalLabelId = AnnotationView & {
    annotation_label: AnnotationView['annotation_label'] & {
        annotation_label_id?: string;
    };
};

const isAnnotationNotFoundError = (error: unknown) => {
    if (typeof error === 'object' && error !== null) {
        const status = (error as { status?: unknown }).status;
        if (status === 404) return true;
    }

    if (!(error instanceof Error)) return false;

    const message = error.message.toLowerCase();
    return message.includes('404') || message.includes('not found');
};

const toAnnotationUpdateInput = ({
    annotation,
    collectionId
}: {
    annotation: AnnotationView;
    collectionId: string;
}): AnnotationUpdateInput | null => {
    const segmentationMask = annotation.segmentation_details?.segmentation_mask;
    if (!segmentationMask) return null;

    return {
        annotation_id: annotation.sample_id,
        collection_id: collectionId,
        bounding_box: getBoundingBox(annotation),
        segmentation_mask: segmentationMask
    };
};

const toAnnotationCreateInput = ({
    annotation,
    labelIdsByName
}: {
    annotation: AnnotationView;
    labelIdsByName: Map<string, string>;
}): AnnotationCreateInput | null => {
    const segmentationMask = annotation.segmentation_details?.segmentation_mask;
    if (!segmentationMask) return null;

    const annotationWithOptionalLabelId = annotation as AnnotationViewWithOptionalLabelId;
    const labelName = annotation.annotation_label.annotation_label_name;
    const annotationLabelId =
        labelIdsByName.get(labelName) ??
        annotationWithOptionalLabelId.annotation_label.annotation_label_id;

    if (!annotationLabelId) {
        console.error(
            `Cannot restore annotation "${annotation.sample_id}" because no label id was found.`
        );
        return null;
    }

    const bbox = getBoundingBox(annotation);
    return {
        parent_sample_id: annotation.parent_sample_id,
        annotation_type: annotation.annotation_type,
        annotation_label_id: annotationLabelId,
        x: bbox.x,
        y: bbox.y,
        width: bbox.width,
        height: bbox.height,
        segmentation_mask: segmentationMask
    };
};

export const restoreOverriddenSegmentationAnnotationsForUndo = async ({
    collectionId,
    overriddenAnnotations,
    labels,
    updateAnnotations,
    createAnnotation
}: {
    collectionId: string;
    overriddenAnnotations: AnnotationView[];
    labels: AnnotationLabelOption[];
    updateAnnotations: (updates: AnnotationUpdateInput[]) => Promise<unknown>;
    createAnnotation: (input: AnnotationCreateInput) => Promise<CreateAnnotationResponse>;
}) => {
    if (!overriddenAnnotations.length) return;

    const labelIdsByName = new Map(
        labels
            .filter(
                (label): label is { annotation_label_id: string; annotation_label_name: string } =>
                    Boolean(label.annotation_label_id && label.annotation_label_name)
            )
            .map((label) => [label.annotation_label_name, label.annotation_label_id])
    );

    for (const annotation of overriddenAnnotations) {
        const updateInput = toAnnotationUpdateInput({ annotation, collectionId });
        if (!updateInput) continue;

        try {
            await updateAnnotations([updateInput]);
            continue;
        } catch (error) {
            if (!isAnnotationNotFoundError(error)) {
                throw error;
            }
        }

        const createInput = toAnnotationCreateInput({ annotation, labelIdsByName });
        if (!createInput) continue;

        await createAnnotation(createInput);
    }
};
