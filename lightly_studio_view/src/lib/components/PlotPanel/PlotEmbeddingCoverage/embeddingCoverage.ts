type HasEmbeddingValue = 'all' | 'yes' | 'no';

export const HAS_EMBEDDING_ITEMS: { value: HasEmbeddingValue; label: string }[] = [
    { value: 'all', label: 'All annotations' },
    { value: 'yes', label: 'Has embedding' },
    { value: 'no', label: 'No embedding' }
];

/**
 * Returns the coverage text, or null when every annotation has an embedding.
 */
export function getCoverageText(
    coverage: { embedded_count: number; total_count: number } | undefined
): string | null {
    if (!coverage || coverage.embedded_count >= coverage.total_count) {
        return null;
    }
    return `${coverage.embedded_count} of ${coverage.total_count} annotations have embeddings`;
}

export function toHasEmbeddingValue(hasEmbedding: boolean | undefined): HasEmbeddingValue {
    if (hasEmbedding === undefined) return 'all';
    return hasEmbedding ? 'yes' : 'no';
}

export function fromHasEmbeddingValue(value: string): boolean | undefined {
    if (value === 'yes') return true;
    if (value === 'no') return false;
    return undefined;
}
