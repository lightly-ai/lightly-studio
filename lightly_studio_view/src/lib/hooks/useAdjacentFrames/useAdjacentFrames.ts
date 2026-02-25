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

    const selectedAnnotationFilterIdsValue = get(selectedAnnotationFilterIds);
    const tagsSelectedValue = get(tagsSelected);
    const videoFramesBounds = get(videoFramesBoundsValues);
    const metadataValuesValue = get(metadataValues);

    const annotationLabelIds = selectedAnnotationFilterIdsValue?.size
        ? Array.from(selectedAnnotationFilterIdsValue)
        : undefined;

    const tagIds = tagsSelectedValue?.size ? Array.from(tagsSelectedValue) : undefined;

    const metadataFilters = metadataValuesValue
        ? createMetadataFilters(metadataValuesValue)
        : undefined;

    return useAdjacentSamples({
        params: {
            sampleId,
            body: {
                sample_type: SampleType.VIDEO_FRAME,
                filters: {
                    sample_filter: {
                        collection_id: collectionId,
                        annotation_label_ids: annotationLabelIds,
                        tag_ids: tagIds,
                        metadata_filters: metadataFilters
                    },
                    ...videoFramesBounds
                }
            }
        }
    });
};
