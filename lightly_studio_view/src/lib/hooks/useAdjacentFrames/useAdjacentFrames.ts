import { SampleType } from '$lib/api/lightly_studio_local';
import { get } from 'svelte/store';
import { useAdjacentSamples } from '../useAdjacentSamples/useAdjacentSamples';
import { useGlobalStorage } from '../useGlobalStorage';
import { useTags } from '../useTags/useTags';
import { useVideoFramesBounds } from '../useVideoFramesBounds/useVideoFramesBounds';
import {
    createMetadataFilters,
    useMetadataFilters
} from '../useMetadataFilters/useMetadataFilters';

export const useAdjacentFrames = ({
    sampleId,
    collectionId
}: {
    sampleId: string;
    collectionId: string;
}) => {
    const { selectedAnnotationFilterIds } = useGlobalStorage();
    const { tagsSelected } = useTags({
        collection_id: collectionId,
        kind: ['sample']
    });
    const { videoFramesBoundsValues } = useVideoFramesBounds();
    const { metadataValues } = useMetadataFilters(collectionId);
    
    return useAdjacentSamples({
        params: {
            sampleId,
            body: {
                sample_type: SampleType.VIDEO_FRAME,
                filters: {
                    sample_filter: {
                        collection_id: collectionId,
                        annotation_label_ids: get(selectedAnnotationFilterIds)?.size
                            ? Array.from(get(selectedAnnotationFilterIds))
                            : undefined,
                        tag_ids:
                            get(tagsSelected).size > 0 ? Array.from(get(tagsSelected)) : undefined,
                        metadata_filters: metadataValues
                            ? createMetadataFilters(get(metadataValues))
                            : undefined
                    },
                    ...get(videoFramesBoundsValues)
                }
            }
        }
    });
};
