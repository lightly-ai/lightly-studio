import { describe, expect, it } from 'vitest';
import { buildSimilarityThresholdFilter } from './buildSimilarityThresholdFilter';

describe('buildSimilarityThresholdFilter', () => {
    it('returns the embedding and threshold when both are set', () => {
        expect(buildSimilarityThresholdFilter([0.1, 0.2], 0)).toEqual({
            text_embedding: [0.1, 0.2],
            min_similarity: 0
        });
    });

    it.each([
        ['no threshold', [0.1], undefined],
        ['no search', undefined, 0.5]
    ])('returns an empty object with %s', (_name, embedding, minSimilarity) => {
        expect(buildSimilarityThresholdFilter(embedding, minSimilarity)).toEqual({});
    });
});
