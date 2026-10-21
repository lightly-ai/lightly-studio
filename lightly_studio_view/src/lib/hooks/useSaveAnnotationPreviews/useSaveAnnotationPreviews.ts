import type { AnnotationPreview } from '$lib/api/lightly_studio_local';
import {
    readAnnotationLabelsOptions,
    readAnnotationLabelsQueryKey
} from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import {
    previewToCreateInput,
    type SaveAs
} from '$lib/components/SampleDetails/AnnotationPreview/annotationPreview.helpers';
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

// Saves accepted previews and reports each saved one, so a retry after a failure only has to
// submit the previews that are left.
export const useSaveAnnotationPreviews = ({
    getCollectionId
}: {
    getCollectionId: () => string;
}) => {
    const { createAnnotation, refetch } = useCreateAnnotation({ getCollectionId });
    const { createLabel } = useCreateLabel({ getCollectionId });
    const client = useQueryClient();

    // Fetches the classes from the server, so classes created by an earlier call are included.
    const fetchLabelIds = async () => {
        const labels = await client.fetchQuery(
            readAnnotationLabelsOptions({ path: { collection_id: getCollectionId() } })
        );
        return new Map(
            labels.map((label): [string, string] => [
                label.annotation_label_name,
                label.annotation_label_id!
            ])
        );
    };

    const getLabelIds = async (classNames: string[]) => {
        const labelIds = await fetchLabelIds();
        const newClassNames = [...new Set(classNames)].filter((name) => !labelIds.has(name));
        for (const className of newClassNames) {
            const label = await createLabel({
                dataset_id: page.params.dataset_id!,
                annotation_label_name: className
            });
            labelIds.set(className, label.annotation_label_id!);
        }
        if (newClassNames.length > 0) {
            client.invalidateQueries({
                queryKey: readAnnotationLabelsQueryKey({
                    path: { collection_id: getCollectionId() }
                })
            });
        }
        return labelIds;
    };

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
