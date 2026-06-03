import {
    computeSimilarityMetadata,
    computeTypicalityMetadata
} from '$lib/api/lightly_studio_local/sdk.gen';
import type { StrategyInstance } from '$lib/hooks/useStrategyBuilder';
import { toast } from 'svelte-sonner';
import { getMetadataKey } from './strategyApiMapping';

interface SelectionError {
    error: string;
}

function handleComputeError(response: { error: unknown }, prefix: string): boolean {
    if (!response.error) return false;
    const detail = (response.error as SelectionError).error ?? 'Unknown error';
    toast.error(`${prefix}: ${detail}`);
    return true;
}

interface ComputeStrategyMetadataParams {
    instance: StrategyInstance;
    collectionId: string;
    isVideoCollection: boolean;
    onProgress: (message: string) => void;
}

export async function computeStrategyMetadata(
    params: ComputeStrategyMetadataParams
): Promise<boolean> {
    const { instance, collectionId, isVideoCollection, onProgress } = params;
    if (instance.type === 'typicality') {
        onProgress('Computing typicality metadata...');
        const response = await computeTypicalityMetadata({
            path: { collection_id: collectionId },
            body: {
                embedding_model_name: null,
                metadata_name: getMetadataKey(instance)
            }
        });
        if (handleComputeError(response, 'Failed to compute typicality metadata')) return false;
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
        if (handleComputeError(response, 'Failed to compute similarity metadata')) return false;
    }

    return true;
}
