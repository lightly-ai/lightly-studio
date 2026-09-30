import { render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSimilarityRange } from '$lib/hooks/useSimilarityRange';
import SimilarityThresholdFilter from './SimilarityThresholdFilter.svelte';

vi.mock('$lib/hooks/useSimilarityRange', () => ({ useSimilarityRange: vi.fn() }));

const defaultProps = {
    collectionId: 'col-1',
    textEmbedding: [0.1, 0.2],
    value: null,
    onCommit: vi.fn(),
    onClear: vi.fn()
};

const mockRange = (data: { min: number; max: number } | null | undefined) => {
    vi.mocked(useSimilarityRange).mockReturnValue({ data } as ReturnType<
        typeof useSimilarityRange
    >);
};

describe('SimilarityThresholdFilter', () => {
    beforeEach(() => {
        vi.mocked(useSimilarityRange).mockReset();
    });

    it('fetches the range of the search in the collection', () => {
        mockRange(undefined);
        render(SimilarityThresholdFilter, { props: defaultProps });

        const getParams = vi.mocked(useSimilarityRange).mock.calls[0][0];
        expect(getParams()).toEqual({ collectionId: 'col-1', textEmbedding: [0.1, 0.2] });
    });

    it('shows the slider for the fetched range', () => {
        mockRange({ min: -0.1, max: 0.3 });
        render(SimilarityThresholdFilter, { props: defaultProps });

        expect(screen.getByText('Similarity search threshold')).toBeInTheDocument();
        expect(screen.getByText('-0.1')).toBeInTheDocument();
        expect(screen.getByText('0.3')).toBeInTheDocument();
    });

    it.each([
        ['while loading', undefined],
        ['without embeddings', null]
    ])('is hidden %s', (_name, data) => {
        mockRange(data);
        render(SimilarityThresholdFilter, { props: defaultProps });

        expect(screen.queryByText('Similarity search threshold')).not.toBeInTheDocument();
    });
});
