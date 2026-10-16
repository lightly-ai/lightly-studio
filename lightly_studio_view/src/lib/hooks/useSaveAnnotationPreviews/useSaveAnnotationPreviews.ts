import type { AnnotationPreview } from '$lib/api/lightly_studio_local';
import { readAnnotationLabelsQueryKey } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import {
    previewToCreateInput,
    type SaveAs
} from '$lib/components/SampleDetails/AnnotationPreview/annotationPreview.helpers';
import { useAnnotationLabels } from '$lib/hooks/useAnnotationLabels/useAnnotationLabels';
import { useCreateAnnotation } from '$lib/hooks/useCreateAnnotation/useCreateAnnotation';
import { useCreateLabel } from '$lib/hooks/useCreateLabel/useCreateLabel';
import { useQueryClient } from '@tanstack/svelte-query';
import { page } from '$app/state';

interface SaveAnnotationPreviewsParams {
    sampleId: string;
    saveAs: SaveAs;
    annotationSource: string | null | undefined;
    previews: { preview: AnnotationPreview; className: string }[];
    onPreviewSaved: (preview: AnnotationPreview) => void;
}

// Saves accepted previews one by one and reports each saved one, so a retry after a failure
// only has to submit the previews that are left.
export const useSaveAnnotationPreviews = ({
    getCollectionId
}: {
    getCollectionId: () => string;
}) => {
    const { createAnnotation } = useCreateAnnotation({ getCollectionId });
    const { createLabel } = useCreateLabel({ getCollectionId });
    const labels = useAnnotationLabels(() => ({ collectionId: getCollectionId() }));
    const client = useQueryClient();
    // Survives across calls, so a retry does not depend on the refetched label list.
    const createdLabelIds = new Map<string, string>();

    const getLabelId = async (labelIds: Map<string, string>, className: string) => {
        const existing = labelIds.get(className);
        if (existing) return existing;
        const label = await createLabel({
            dataset_id: page.params.dataset_id!,
            annotation_label_name: className
        });
        createdLabelIds.set(className, label.annotation_label_id!);
        labelIds.set(className, label.annotation_label_id!);
        await client.invalidateQueries({
            queryKey: readAnnotationLabelsQueryKey({ path: { collection_id: getCollectionId() } })
        });
        return label.annotation_label_id!;
    };

    const saveAnnotationPreviews = async (params: SaveAnnotationPreviewsParams) => {
        const labelIds = new Map([
            ...(labels.data ?? []).map((label): [string, string] => [
                label.annotation_label_name,
                label.annotation_label_id!
            ]),
            ...createdLabelIds
        ]);
        for (const { preview, className } of params.previews) {
            await createAnnotation({
                parent_sample_id: params.sampleId,
                annotation_label_id: await getLabelId(labelIds, className),
                annotation_collection_name: params.annotationSource || undefined,
                ...previewToCreateInput({ preview, saveAs: params.saveAs })
            });
            params.onPreviewSaved(preview);
        }
    };

    return { saveAnnotationPreviews };
};
