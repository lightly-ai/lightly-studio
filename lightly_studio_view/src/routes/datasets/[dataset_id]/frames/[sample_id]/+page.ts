import type { PageLoad } from './$types';
import {
    useFrameAdjacents,
    type FrameAdjacents
} from '$lib/hooks/useFramesAdjacents/useFramesAdjacents';
import { get, type Writable } from 'svelte/store';
import type { VideoFrameFieldsBoundsView, VideoFrameFilter } from '$lib/api/lightly_studio_local';
import type { MetadataValues } from '$lib/services/types';
import {
    createMetadataFilters,
    useMetadataFilters
} from '$lib/hooks/useMetadataFilters/useMetadataFilters';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { useTags } from '$lib/hooks/useTags/useTags';
import { useVideoFramesBounds } from '$lib/hooks/useVideoFramesBounds/useVideoFramesBounds';

function buildVideoFramesFilters({
    tagIds,
    metadata,
    annotationIds,
    bounds
}: {
    tagIds: Set<string>;
    metadata: MetadataValues;
    annotationIds: Set<string>;
    bounds: VideoFrameFieldsBoundsView | null;
}): VideoFrameFilter {
    return {
        sample_filter: {
            tag_ids: tagIds.size > 0 ? [...tagIds] : undefined,
            metadata_filters: metadata ? createMetadataFilters(metadata) : undefined,
            annotation_label_ids: [...annotationIds]
        },
        ...bounds
    };
}

export const load: PageLoad = async ({ params, url }) => {
    const datasetId = params.dataset_id;

    const indexParam = url.searchParams.get('index');
    const frameIndex = indexParam !== null ? parseInt(indexParam) : null;

    let frameAdjacents: Writable<FrameAdjacents> | null = null;

    if (frameIndex !== null) {
        const { selectedAnnotationFilterIds } = useGlobalStorage();
        const { videoFramesBoundsValues } = useVideoFramesBounds();
        const { metadataValues } = useMetadataFilters();

        const { tagsSelected } = useTags({
            dataset_id: datasetId,
            kind: ['sample']
        });

        const tagIds = get(tagsSelected);
        const metadata = get(metadataValues);
        const annotationIds = get(selectedAnnotationFilterIds);
        const bounds = get(videoFramesBoundsValues);

        const filter = buildVideoFramesFilters({
            tagIds,
            metadata,
            annotationIds,
            bounds
        });

        frameAdjacents = useFrameAdjacents({
            video_frame_dataset_id: datasetId,
            sampleIndex: frameIndex,
            filter
        });
    }

    return {
        frameAdjacents: frameAdjacents,
        frameIndex: frameIndex,
        dataset_id: params.dataset_id,
        sampleId: params.sample_id
    };
};
