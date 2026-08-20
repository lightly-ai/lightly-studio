import { SampleType } from '$lib/api/lightly_studio_local';
import { get } from 'svelte/store';
import { useAdjacentSamples } from '../useAdjacentSamples/useAdjacentSamples';
import { useAnnotationSortBy } from '$lib/hooks';
import { useGlobalStorage } from '../useGlobalStorage';
import { useTags } from '../useTags/useTags';

export const useAdjacentAnnotations = ({
    sampleId,
    collectionId
}: {
    sampleId: string;
    collectionId: string;
}) => {
    const { selectedAnnotationFilterIds, textEmbedding } = useGlobalStorage();
    const { tagsSelected } = useTags({ collection_id: collectionId });
    const { getSortBy } = useAnnotationSortBy();
    const embedding = get(textEmbedding);
    const sortBy = embedding ? undefined : (getSortBy(collectionId) ?? undefined);

    return useAdjacentSamples({
        params: {
            sampleId,
            body: {
                sample_type: SampleType.ANNOTATION,
                collection_id: collectionId,
                filters: {
                    filter_type: 'annotations',
                    collection_ids: [collectionId],
                    annotation_label_ids:
                        get(selectedAnnotationFilterIds).size > 0
                            ? Array.from(get(selectedAnnotationFilterIds))
                            : undefined,
                    tag_ids: get(tagsSelected).size > 0 ? Array.from(get(tagsSelected)) : undefined
                },
                annotation_sort_by: sortBy
            }
        }
    });
};
