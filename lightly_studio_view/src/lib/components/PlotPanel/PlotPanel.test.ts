import { render, screen } from '@testing-library/svelte';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import PlotPanel from './PlotPanel.svelte';
import { writable } from 'svelte/store';
import { useEmbeddings } from '$lib/hooks/useEmbeddings/useEmbeddings';

vi.mock('$app/state', () => ({
    page: {
        params: { dataset_id: 'test-dataset-id' }
    }
}));

// Mock dependencies
vi.mock('embedding-atlas/svelte', () => ({
    EmbeddingView: class MockEmbeddingView {}
}));
vi.mock('$lib/hooks/useEmbeddings/useEmbeddings');
vi.mock('$lib/hooks/useImageFilters/useImageFilters', () => ({
    useImageFilters: () => ({
        filterParams: writable({ mode: 'normal', filters: {} }),
        imageFilter: writable({}),
        updateFilterParams: vi.fn()
    })
}));
vi.mock('$lib/hooks/useGlobalStorage', () => {
    const rangeSelection = writable(null);
    const getRangeSelection = vi.fn(() => rangeSelection);
    const setRangeSelectionForDataset = vi.fn();
    return {
        useGlobalStorage: () => ({
            setShowPlot: vi.fn(),
            getRangeSelection,
            setRangeSelectionForDataset
        })
    };
});

describe('PlotPanel.svelte error handling', () => {
    beforeEach(() => {
        vi.resetAllMocks();
    });

    it('should display an error message when useEmbeddings returns an error object', async () => {
        const mockError = { error: 'Test error from object' };
        (useEmbeddings as vi.Mock).mockReturnValue(
            writable({
                isError: true,
                error: mockError,
                isLoading: false,
                data: null
            })
        );

        render(PlotPanel);

        const expectedMessage = `Error loading embeddings: ${mockError.error}`;
        const errorMessage = await screen.findByText(expectedMessage);
        expect(errorMessage).toBeInTheDocument();
    });
});
