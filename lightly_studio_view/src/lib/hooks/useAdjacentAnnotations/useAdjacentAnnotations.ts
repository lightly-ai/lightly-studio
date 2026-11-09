import { SampleType, type AnnotationsFilter } from '$lib/api/lightly_studio_local';
import { get } from 'svelte/store';
import { useAdjacentSamples } from '../useAdjacentSamples/useAdjacentSamples';
import { useAnnotationSortBy } from '$lib/hooks';
import { useGlobalStorage } from '../useGlobalStorage';
import { useTags } from '../useTags/useTags';

export const useAdjacentAnnotations = ({
    sampleId,
    collectionId,
    treeFilter
}: {
    sampleId: string;
    collectionId: string;
    /** The annotation tree filter of the Annotations grid. Set only when the grid shows the tree. */
    treeFilter?: Pick<AnnotationsFilter, 'annotation_pairs'>;
}) => {
    const { selectedAnnotationFilterIds, textEmbedding } = useGlobalStorage();
    const { tagsSelected } = useTags({ collection_id: collectionId });
    const { getSortBy } = useAnnotationSortBy();
    const embedding = get(textEmbedding);
    const sortBy = embedding ? undefined : (getSortBy(collectionId) ?? undefined);

    const adjacentSamples = useAdjacentSamples({
        params: {
            sampleId,
            body: {
                sample_type: SampleType.ANNOTATION,
                collection_id: collectionId,
                filters: {
                    filter_type: 'annotations',
                    collection_ids: [collectionId],
                    ...(treeFilter
                        ? { annotation_pairs: treeFilter.annotation_pairs }
                        : {
                              annotation_label_ids:
                                  get(selectedAnnotationFilterIds).size > 0
                                      ? Array.from(get(selectedAnnotationFilterIds))
                                      : undefined
                          }),
                    tag_ids: get(tagsSelected).size > 0 ? Array.from(get(tagsSelected)) : undefined
                },
                annotation_sort_by: sortBy
            }
        }
    });

    // The selected sort is not always the applied one, so callers get what the query really used.
    return { ...adjacentSamples, sortBy };
};
