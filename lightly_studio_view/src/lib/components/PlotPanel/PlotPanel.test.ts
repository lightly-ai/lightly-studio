import { render, screen } from '@testing-library/svelte';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import PlotPanel from './PlotPanel.svelte';
import { useEmbeddings } from '$lib/hooks/useEmbeddings/useEmbeddings';
import { writable } from 'svelte/store';

vi.mock('$app/state', () => ({
    page: {
        params: { collection_id: 'test-collection-id' }
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
    return {
        useGlobalStorage: () => ({
            setShowPlot: vi.fn(),
            getRangeSelection: vi.fn(() => writable(null)),
            setRangeSelectionForcollection: vi.fn()
        })
    };
});

describe('PlotPanel.svelte error handling', () => {
    beforeEach(() => {
        vi.resetAllMocks();
    });

    it('should display an error message when useEmbeddings returns an error object', async () => {
        const mockError: Error = { name: 'TestError', message: 'Test error from object' };
        (useEmbeddings as vi.Mock).mockReturnValue(
            writable({
                isError: true,
                error: mockError,
                isLoading: false,
                data: null
            })
        );

        render(PlotPanel);

        const expectedMessage = `Error loading embeddings: ${mockError.message}`;
        const errorMessage = await screen.findByText(expectedMessage);
        expect(errorMessage).toBeInTheDocument();
    });
});
