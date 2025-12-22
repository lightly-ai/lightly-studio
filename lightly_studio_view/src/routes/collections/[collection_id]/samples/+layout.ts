import { useDimensions } from '$lib/hooks/useDimensions/useDimensions';
import type { LayoutLoad, LayoutLoadEvent } from './$types';

import { useTags } from '$lib/hooks/useTags/useTags';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

export type LayoutLoadResult = {
    samplesSelectedTagsIds: ReturnType<typeof useTags>['tagsSelected'];
    samplesDimensions: ReturnType<typeof useDimensions>['dimensionsValues'];
    samplesTextEmbedding: ReturnType<typeof useGlobalStorage>['textEmbedding'];
    samplesSelectedAnnotationLabelsIds: ReturnType<
        typeof useGlobalStorage
    >['selectedAnnotationFilterIds'];
};

export const load: LayoutLoad = async ({
    params: { collection_id }
}: LayoutLoadEvent): Promise<LayoutLoadResult> => {
    const { selectedAnnotationFilterIds, textEmbedding } = useGlobalStorage();

    const { tagsSelected } = useTags({
        collection_id: collection_id as string,
        kind: ['sample']
    });

    const { dimensionsValues } = useDimensions();

    return {
        samplesSelectedTagsIds: tagsSelected,
        samplesDimensions: dimensionsValues,
        samplesTextEmbedding: textEmbedding,
        samplesSelectedAnnotationLabelsIds: selectedAnnotationFilterIds
    };
};
