import { useSampleAdjacents } from '$lib/hooks/useSampleAdjacents/useSampleAdjacents';
import { get } from 'svelte/store';
import type { PageLoad } from './$types';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

export const load: PageLoad = async ({
    parent,
    params: { dataset_id, sampleId, sampleIndex: sampleIndexParam }
}) => {
    const {
        samplesSelectedTagsIds,
        samplesSelectedAnnotationLabelsIds,
        samplesDimensions,
        samplesTextEmbedding
    } = await parent();

    const sampleIndex = parseInt(sampleIndexParam, 10);

    const { metadataValues } = useGlobalStorage();
    const sampleAdjacents = useSampleAdjacents({
        dataset_id,
        sampleId,
        sampleIndex,
        tagIds: Array.from(get(samplesSelectedTagsIds)),
        annotationLabelIds: Array.from(get(samplesSelectedAnnotationLabelsIds)),
        min_width: get(samplesDimensions)?.min_width,
        max_width: get(samplesDimensions)?.max_width,
        min_height: get(samplesDimensions)?.min_height,
        max_height: get(samplesDimensions)?.max_height,
        textEmbedding: get(samplesTextEmbedding)?.embedding,
        metadataValues: get(metadataValues)
    });

    return { sampleAdjacents, sampleIndex };
};
