import type { AnnotationPreview } from '$lib/api/lightly_studio_local';
import {
    previewToCreateInput,
    type OutputType
} from '$lib/components/SampleDetails/AnnotationPreview/annotationPreview.helpers';
import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
import { useCreateAnnotation } from '$lib/hooks/useCreateAnnotation/useCreateAnnotation';
import { useCreateLabel } from '$lib/hooks/useCreateLabel/useCreateLabel';
import { page } from '$app/state';

interface SaveAnnotationPreviewsParams {
    sampleId: string;
    image: { width: number; height: number };
    outputType: OutputType;
    annotationSource: string | null | undefined;
    previews: { preview: AnnotationPreview; className: string }[];
}

// Saves accepted AI-assisted labeling previews as annotations. Creates missing annotation
// classes on the way.
export const useSaveAnnotationPreviews = ({
    getCollectionId
}: {
    getCollectionId: () => string;
}) => {
    const { createAnnotation } = useCreateAnnotation({ getCollectionId });
    const { createLabel } = useCreateLabel({ getCollectionId });
    const labels = useAnnotationLabels(() => ({ collectionId: getCollectionId() }));

    const getLabelId = async (labelIds: Map<string, string>, className: string) => {
        const existing = labelIds.get(className);
        if (existing) return existing;
        const label = await createLabel({
            dataset_id: page.params.dataset_id!,
            annotation_label_name: className
        });
        labelIds.set(className, label.annotation_label_id!);
        return label.annotation_label_id!;
    };

    const saveAnnotationPreviews = async (params: SaveAnnotationPreviewsParams) => {
        const labelIds = new Map(
            (labels.data ?? []).map((label) => [
                label.annotation_label_name,
                label.annotation_label_id!
            ])
        );
        for (const { preview, className } of params.previews) {
            await createAnnotation({
                parent_sample_id: params.sampleId,
                annotation_label_id: await getLabelId(labelIds, className),
                annotation_collection_name: params.annotationSource || undefined,
                ...previewToCreateInput({
                    preview,
                    outputType: params.outputType,
                    image: params.image
                })
            });
        }
    };

    return { saveAnnotationPreviews };
};
