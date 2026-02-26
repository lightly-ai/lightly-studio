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
    fromVideos?: boolean
}) => {
    let filters: VideoFrameAdjacentFilter

    if (fromVideos) {
        const { videoFilter } = useVideoFilters();
        const { textEmbedding } = useGlobalStorage();

        filters = {
                    video_frame_filter: {
                        sample_filter: {
                            collection_id: collectionId
                        },
                        frame_number: {}
                    },
                    video_filter: get(videoFilter),
                    video_text_embedding: get(textEmbedding)?.embedding
        }
    } else {
        const { frameFilter } = useFramesFilter();

        filters = {
             video_frame_filter: get(frameFilter) ?? {
                sample_filter: {
                    collection_id: collectionId
                },
                frame_number: {}
            },
        }
    }

    return useAdjacentSamples({
        params: {
            sampleId,
            body: {
                sample_type: SampleType.VIDEO_FRAME,
                filters,
            }
        }
    });
};
