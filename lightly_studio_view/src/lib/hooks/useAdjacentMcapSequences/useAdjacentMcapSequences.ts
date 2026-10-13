import { SampleType } from '$lib/api/lightly_studio_local';
import { useAdjacentSamples } from '../useAdjacentSamples/useAdjacentSamples';

/** Previous/next MCAP sequence in the order of the sequences grid. */
export const useAdjacentMcapSequences = ({
    sampleId,
    collectionId
}: {
    sampleId: string;
    collectionId: string;
}) =>
    useAdjacentSamples({
        params: {
            sampleId,
            body: {
                sample_type: SampleType.SEQUENCE,
                collection_id: collectionId
            }
        }
    });
