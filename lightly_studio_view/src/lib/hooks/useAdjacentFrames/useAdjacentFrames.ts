import { SampleType, type VideoFrameAdjacentFilter } from '$lib/api/lightly_studio_local';
import { get } from 'svelte/store';
import { useAdjacentSamples } from '../useAdjacentSamples/useAdjacentSamples';
import { useFramesFilter } from '../useFramesFilter/useFramesFilter';
import { useVideoFilters } from '../useVideoFilters/useVideoFilters';
import { useGlobalStorage } from '../useGlobalStorage';

export const useAdjacentFrames = ({
    sampleId,
    collectionId,
    fromVideos = false
}: {
    sampleId: string;
    collectionId: string;
    fromVideos?: boolean;
}) => {
    let filters: { filter_type: 'video_frame_adjacent' } & VideoFrameAdjacentFilter;

    if (fromVideos) {
        const { videoFilter } = useVideoFilters();
        const { textEmbedding } = useGlobalStorage();
        const videoFilterValue = get(videoFilter);
        const videoCollectionId = videoFilterValue?.sample_filter?.collection_id;

        filters = {
            filter_type: 'video_frame_adjacent',
            video_frame_filter: {
                collection_id: collectionId,
                filter: {
                    frame_number: {}
                }
            },
            video_filter:
                videoFilterValue && videoCollectionId
                    ? { collection_id: videoCollectionId, filter: videoFilterValue }
                    : undefined,
            video_text_embedding: get(textEmbedding)?.embedding
        } as { filter_type: 'video_frame_adjacent' } & VideoFrameAdjacentFilter;
    } else {
        const { frameFilter } = useFramesFilter();

        filters = {
            filter_type: 'video_frame_adjacent',
            video_frame_filter: {
                collection_id: collectionId,
                filter: get(frameFilter) ?? { frame_number: {} }
            }
        } as { filter_type: 'video_frame_adjacent' } & VideoFrameAdjacentFilter;
    }

    return useAdjacentSamples({
        params: {
            sampleId,
            body: {
                sample_type: SampleType.VIDEO_FRAME,
                filters
            }
        }
    });
};
