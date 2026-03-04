import { SampleType } from '$lib/api/lightly_studio_local';
import { get } from 'svelte/store';
import { useAdjacentSamples } from '../useAdjacentSamples/useAdjacentSamples';
import { useGlobalStorage } from '../useGlobalStorage';
import { useTags } from '../useTags/useTags';

export const useAdjacentAnnotations = ({
    sampleId,
    collectionId
}: {
    sampleId: string;
    collectionId: string;
}) => {
    const { selectedAnnotationFilterIds } = useGlobalStorage();
    const { tagsSelected } = useTags({ collection_id: collectionId });

    return useAdjacentSamples({
        params: {
            sampleId,
            body: {
                sample_type: SampleType.ANNOTATION,
                filters: {
                    collection_ids: [collectionId],
                    annotation_label_ids:
                        get(selectedAnnotationFilterIds).size > 0
                            ? Array.from(get(selectedAnnotationFilterIds))
                            : undefined,
                    annotation_tag_ids:
                        get(tagsSelected).size > 0 ? Array.from(get(tagsSelected)) : undefined
                }
            }
        }
    });
};
