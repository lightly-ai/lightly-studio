import type { PageLoad } from './$types';
import { getVideoById, type VideoFieldsBoundsView } from '$lib/api/lightly_studio_local';
import { get, type Writable } from 'svelte/store';

import {
    useVideoAdjacents,
    type VideoAdjacents
} from '$lib/hooks/useVideoAdjacents/useVideoAdjancents';

import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { useTags } from '$lib/hooks/useTags/useTags';
import { useVideoBounds } from '$lib/hooks/useVideosBounds/useVideosBounds';
import {
    createMetadataFilters,
    useMetadataFilters
} from '$lib/hooks/useMetadataFilters/useMetadataFilters';
import type { MetadataValues } from '$lib/services/types';

function buildVideoFilters({
    tagIds,
    metadata,
    annotationIds,
    bounds,
    includeNoAnnotations
}: {
    tagIds: Set<string>;
    metadata: MetadataValues;
    annotationIds: Set<string>;
    bounds: VideoFieldsBoundsView | null;
    includeNoAnnotations: boolean;
}) {
    return {
        sample_filter: {
            tag_ids: tagIds.size > 0 ? [...tagIds] : undefined,
            metadata_filters: metadata ? createMetadataFilters(metadata) : undefined
        },
        annotation_frames_label_ids: [...annotationIds],
        include_no_annotations: includeNoAnnotations ? true : undefined,
        ...bounds
    };
}

export const load: PageLoad = async ({ params, url }) => {
    const collectionId = params.collection_id;
    const sampleId = params.sample_id;

    const indexParam = url.searchParams.get('index');
    const videoIndex = indexParam !== null ? Number(indexParam) : null;

    let videoAdjacents: Writable<VideoAdjacents> | null = null;

    if (videoIndex !== null) {
        const { selectedAnnotationFilterIds, selectedNoAnnotationsFilter } = useGlobalStorage();
        const { videoBoundsValues } = useVideoBounds();
        const { metadataValues } = useMetadataFilters();

        const { tagsSelected } = useTags({
            collection_id: collectionId,
            kind: ['sample']
        });

        const tagIds = get(tagsSelected);
        const metadata = get(metadataValues);
        const annotationIds = get(selectedAnnotationFilterIds);
        const bounds = get(videoBoundsValues);
        const includeNoAnnotations = get(selectedNoAnnotationsFilter);

        const filter = buildVideoFilters({
            tagIds,
            metadata,
            annotationIds,
            bounds,
            includeNoAnnotations
        });

        videoAdjacents = useVideoAdjacents({
            collection_id: collectionId,
            sampleIndex: videoIndex,
            filter
        });
    }

    const sampleResponse = await getVideoById({
        path: { sample_id: sampleId }
    });

    return {
        sample: sampleResponse.data,
        videoIndex,
        videoAdjacents
    };
};
