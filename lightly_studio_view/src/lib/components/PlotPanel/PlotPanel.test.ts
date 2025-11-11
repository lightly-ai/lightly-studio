import { render, screen } from '@testing-library/svelte';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import PlotPanel from './PlotPanel.svelte';
import { writable } from 'svelte/store';
import { useEmbeddings } from '$lib/hooks/useEmbeddings/useEmbeddings';

// Mock dependencies
vi.mock('embedding-atlas/svelte', () => ({
    EmbeddingView: class MockEmbeddingView {}
}));
vi.mock('$lib/hooks/useEmbeddings/useEmbeddings');
vi.mock('$lib/hooks/useSamplesFilters/useSamplesFilters', () => ({
    useSamplesFilters: () => ({
        filterParams: writable({ mode: 'normal', filters: {} }),
        imageFilter: writable({}),
        updateFilterParams: vi.fn()
    })
}));
vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        setShowPlot: vi.fn()
    })
}));

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
