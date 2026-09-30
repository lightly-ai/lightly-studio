import type { SampleFilter } from '$lib/api/lightly_studio_local';

type SimilarityThresholdFilter = Pick<SampleFilter, 'text_embedding' | 'min_similarity'>;

/**
 * Returns the threshold fields for a sample filter, or an empty object while no threshold is
 * set. The filter carries its own copy of the embedding, because select-all and tag-by-filter
 * receive only the filter.
 */
export const buildSimilarityThresholdFilter = (
    textEmbedding: number[] | null | undefined,
    minSimilarity: number | null | undefined
): SimilarityThresholdFilter => {
    if (!textEmbedding || minSimilarity == null) {
        return {};
    }
    return { text_embedding: textEmbedding, min_similarity: minSimilarity };
};
