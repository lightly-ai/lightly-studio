import { getSimilarityRangeOptions } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createQuery } from '@tanstack/svelte-query';

interface UseSimilarityRangeParams {
    collectionId: string;
    textEmbedding: number[];
}

/** Fetches the min and max similarity of a text search to all samples of a collection. */
export const useSimilarityRange = (getParams: () => UseSimilarityRangeParams) =>
    createQuery(() => {
        const { collectionId, textEmbedding } = getParams();
        return getSimilarityRangeOptions({
            path: { collection_id: collectionId },
            body: { text_embedding: textEmbedding }
        });
    });
