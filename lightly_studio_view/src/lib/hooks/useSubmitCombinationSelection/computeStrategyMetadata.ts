import {
    computeSimilarityMetadata,
    computeTypicalityMetadata
} from '$lib/api/lightly_studio_local/sdk.gen';
import type { StrategyInstance } from '$lib/hooks/useStrategyBuilder';
import { toast } from 'svelte-sonner';
import { getMetadataKey } from './strategyApiMapping';

type SelectionError = { error: string };

export async function computeStrategyMetadata(
    instance: StrategyInstance,
    collectionId: string,
    isVideoCollection: boolean,
    onProgress: (message: string) => void
): Promise<boolean> {
    if (instance.type === 'typicality') {
        onProgress('Computing typicality metadata...');
        const response = await computeTypicalityMetadata({
            path: { collection_id: collectionId },
            body: {
                embedding_model_name: null,
                metadata_name: getMetadataKey(instance)
            }
        });
        if (response.error) {
            toast.error(
                'Failed to compute typicality metadata: ' +
                    ((response.error as SelectionError).error ?? 'Unknown error')
            );
            return false;
        }
    }

    if (instance.type === 'similarity') {
        if (isVideoCollection) {
            toast.error('Similarity is only available for image collections.');
            return false;
        }
        onProgress('Computing similarity metadata...');
        const response = await computeSimilarityMetadata({
            path: {
                collection_id: collectionId,
                query_tag_id: instance.params.query_tag_id
            },
            body: {
                embedding_model_name: null,
                metadata_name: getMetadataKey(instance)
            }
        });
        if (response.error) {
            toast.error(
                'Failed to compute similarity metadata: ' +
                    ((response.error as SelectionError).error ?? 'Unknown error')
            );
            return false;
        }
    }

    return true;
}
