import { describe, expect, it } from 'vitest';
import { fromHasEmbeddingValue, getCoverageText, toHasEmbeddingValue } from './embeddingCoverage';

describe('getCoverageText', () => {
    it('describes the coverage when some annotations have no embedding', () => {
        expect(getCoverageText({ embedded_count: 1, total_count: 100 })).toBe(
            '1 of 100 annotations have embeddings'
        );
    });

    it('returns null when every annotation has an embedding', () => {
        expect(getCoverageText({ embedded_count: 100, total_count: 100 })).toBeNull();
    });

    it('returns null without data', () => {
        expect(getCoverageText(undefined)).toBeNull();
    });
});

describe('has embedding value', () => {
    it.each([
        [undefined, 'all'],
        [true, 'yes'],
        [false, 'no']
    ] as const)('maps %s to %s and back', (hasEmbedding, value) => {
        expect(toHasEmbeddingValue(hasEmbedding)).toBe(value);
        expect(fromHasEmbeddingValue(value)).toBe(hasEmbedding);
    });
});
