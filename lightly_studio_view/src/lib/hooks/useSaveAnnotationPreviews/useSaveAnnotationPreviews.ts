import type { AnnotationPreview } from '$lib/api/lightly_studio_local';
import { useCreateAnnotation } from '$lib/hooks';
import { useLabelIds } from './useLabelIds';
import { previewToCreateInput } from './useSaveAnnotationPreviews.helpers';

interface SaveAnnotationPreviewsParams {
    sampleId: string;
    saveAs: Parameters<typeof previewToCreateInput>[0]['saveAs'];
    annotationSource: string | null | undefined;
    previews: { preview: AnnotationPreview; className: string }[];
    onPreviewSaved: (preview: AnnotationPreview) => void;
}

// Saves accepted previews and reports each saved one, so a retry after a failure only has to
// submit the previews that are left.
export const useSaveAnnotationPreviews = ({
    getCollectionId,
    getDatasetId
}: {
    getCollectionId: () => string;
    getDatasetId: () => string;
}) => {
    const { createAnnotation, refetch } = useCreateAnnotation({ getCollectionId });
    const { getLabelIds } = useLabelIds({ getCollectionId, getDatasetId });

    const saveAnnotationPreviews = async (params: SaveAnnotationPreviewsParams) => {
        const labelIds = await getLabelIds(params.previews.map(({ className }) => className));
        // Sequential, because one mutation only resolves the callbacks of its last call.
        try {
            for (const { preview, className } of params.previews) {
                await createAnnotation(
                    {
                        parent_sample_id: params.sampleId,
                        annotation_label_id: labelIds.get(className)!,
                        annotation_collection_name: params.annotationSource || undefined,
                        ...previewToCreateInput({ preview, saveAs: params.saveAs })
                    },
                    { skipRefetch: true }
                );
                params.onPreviewSaved(preview);
            }
        } finally {
            refetch();
        }
    };

    return { saveAnnotationPreviews };
};
