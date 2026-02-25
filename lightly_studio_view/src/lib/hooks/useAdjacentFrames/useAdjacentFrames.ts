import { SampleType } from '$lib/api/lightly_studio_local';
import { get } from 'svelte/store';
import { useAdjacentSamples } from '../useAdjacentSamples/useAdjacentSamples';
import { useFramesFilter } from '../useFramesFilter/useFramesFilter';

export const useAdjacentFrames = ({
    sampleId,
    collectionId
}: {
    sampleId: string;
    collectionId: string;
}) => {
    const { frameFilter } = useFramesFilter();

    return useAdjacentSamples({
        params: {
            sampleId,
            body: {
                sample_type: SampleType.VIDEO_FRAME,
                filters: get(frameFilter) ?? {
                    sample_filter: {
                        collection_id: collectionId
                    },
                    frame_number: {}
                }
            }
        }
    });
};
