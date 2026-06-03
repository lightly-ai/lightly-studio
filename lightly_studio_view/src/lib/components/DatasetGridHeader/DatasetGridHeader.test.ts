import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import { derived, readable, writable } from 'svelte/store';
import '@testing-library/jest-dom';

vi.mock('$lib/hooks/useGlobalStorage', () => {
    const activePanel = writable<string>('none');
    const showEmbeddingPlot = derived(activePanel, ($p) => $p === 'embeddingPlot');
    const showEvaluationRuns = derived(activePanel, ($p) => $p === 'evaluationRuns');
    const setShowEmbeddingPlot = vi.fn((value: boolean) =>
        activePanel.update((p: string) =>
            value ? 'embeddingPlot' : p === 'embeddingPlot' ? 'none' : p
        )
    );
    const setShowEvaluationRuns = vi.fn((value: boolean) =>
        activePanel.update((p: string) =>
            value ? 'evaluationRuns' : p === 'evaluationRuns' ? 'none' : p
        )
    );
    return {
        useGlobalStorage: () => ({
            activePanel,
            showEmbeddingPlot,
            setShowEmbeddingPlot,
            showEvaluationRuns,
            setShowEvaluationRuns,
            sampleSize: writable({ width: 4, height: 4 }),
            updateSampleSize: vi.fn()
        })
    };
});

vi.mock('$lib/hooks/useOrderBy/useOrderBy', () => ({
    useOrderBy: () => ({
        allSortFields: readable([]),
        selectedDirection: readable('asc'),
        selectedLabel: readable(null),
        isFieldSelected: readable(() => false),
        handleFieldClick: vi.fn(),
        toggleDirection: vi.fn(),
        dispose: vi.fn()
    })
}));

vi.mock('$lib/hooks/useFileDrop/useFileDrop', () => ({
    useFileDrop: () => ({
        dragOver: writable(false),
        handleDragOver: vi.fn(),
        handleDragLeave: vi.fn(),
        handleDrop: vi.fn(),
        handlePaste: vi.fn(),
        handleFileSelect: vi.fn()
    })
}));

import DatasetGridHeader from './DatasetGridHeader.svelte';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

const defaultProps = {
    canSelectAll: false,
    isImages: false,
    hasEvaluationRuns: true,
    hasMediaWithEmbeddings: false,
    collectionDatasetId: 'dataset-1',
    onSelectAll: vi.fn().mockResolvedValue(undefined),
    searchImage: undefined,
    searchPending: false,
    initialQueryText: '',
    onSubmitText: vi.fn(),
    onSubmitFile: vi.fn(),
    onSearchClear: vi.fn(),
    onSearchError: vi.fn()
};

describe('DatasetGridHeader', () => {
    beforeEach(() => {
        const storage = useGlobalStorage();
        storage.activePanel.set('none');
        (storage.setShowEmbeddingPlot as ReturnType<typeof vi.fn>).mockClear();
        (storage.setShowEvaluationRuns as ReturnType<typeof vi.fn>).mockClear();
        defaultProps.onSelectAll.mockClear();
    });

    it('renders the select-all button when canSelectAll is true', async () => {
        render(DatasetGridHeader, {
            props: { ...defaultProps, canSelectAll: true }
        });

        const button = screen.getByTestId('select-all-button');
        expect(button).toBeInTheDocument();

        await fireEvent.click(button);
        expect(defaultProps.onSelectAll).toHaveBeenCalledTimes(1);
    });

    it('does not render the select-all button when canSelectAll is false', () => {
        render(DatasetGridHeader, { props: { ...defaultProps, canSelectAll: false } });

        expect(screen.queryByTestId('select-all-button')).not.toBeInTheDocument();
    });

    it('renders the OrderBy control only for image collections', () => {
        const { unmount } = render(DatasetGridHeader, {
            props: { ...defaultProps, isImages: true }
        });
        expect(screen.getByTestId('sort-by-trigger')).toBeInTheDocument();
        unmount();

        render(DatasetGridHeader, { props: { ...defaultProps } });
        expect(screen.queryByTestId('sort-by-trigger')).not.toBeInTheDocument();
    });

    it('shows the embeddings toggle when media has embeddings', () => {
        render(DatasetGridHeader, {
            props: { ...defaultProps, isImages: true, hasMediaWithEmbeddings: true }
        });

        expect(screen.getByTestId('toggle-plot-button')).toBeInTheDocument();
        expect(screen.getByText('Embeddings')).toBeInTheDocument();
    });

    it('hides the embeddings toggle when media has no embeddings', () => {
        render(DatasetGridHeader, {
            props: { ...defaultProps, isImages: true, hasMediaWithEmbeddings: false }
        });

        expect(screen.queryByTestId('toggle-plot-button')).not.toBeInTheDocument();
    });

    it('toggles the plot store when the embeddings button is clicked', async () => {
        const { setShowEmbeddingPlot } = useGlobalStorage();

        render(DatasetGridHeader, {
            props: { ...defaultProps, isImages: true, hasMediaWithEmbeddings: true }
        });

        const toggle = screen.getByTestId('toggle-plot-button');
        await fireEvent.click(toggle);
        expect(setShowEmbeddingPlot).toHaveBeenLastCalledWith(true);

        await fireEvent.click(toggle);
        expect(setShowEmbeddingPlot).toHaveBeenLastCalledWith(false);
    });

    it('renders the search region when media has embeddings', () => {
        const { container } = render(DatasetGridHeader, {
            props: { ...defaultProps, isImages: true, hasMediaWithEmbeddings: true }
        });

        expect(container.querySelector('[data-grid-search-drop-target]')).toBeInTheDocument();
    });

    it('hides the search region when media has no embeddings', () => {
        const { container } = render(DatasetGridHeader, {
            props: { ...defaultProps, isImages: true, hasMediaWithEmbeddings: false }
        });

        expect(container.querySelector('[data-grid-search-drop-target]')).not.toBeInTheDocument();
    });

    it('shows the evaluation runs toggle for image collections with evaluations', () => {
        render(DatasetGridHeader, {
            props: { ...defaultProps, isImages: true, hasEvaluationRuns: true }
        });

        expect(screen.getByTestId('toggle-evaluation-runs-button')).toBeInTheDocument();
        expect(screen.getByText('Evaluation')).toBeInTheDocument();
    });

    it('hides the evaluation runs toggle for non-image collections', () => {
        render(DatasetGridHeader, { props: { ...defaultProps, isImages: false } });

        expect(screen.queryByTestId('toggle-evaluation-runs-button')).not.toBeInTheDocument();
    });

    it('toggles the evaluation runs store when the button is clicked', async () => {
        const { setShowEvaluationRuns } = useGlobalStorage();

        render(DatasetGridHeader, {
            props: { ...defaultProps, isImages: true, hasEvaluationRuns: true }
        });

        const toggle = screen.getByTestId('toggle-evaluation-runs-button');
        await fireEvent.click(toggle);
        expect(setShowEvaluationRuns).toHaveBeenLastCalledWith(true);

        await fireEvent.click(toggle);
        expect(setShowEvaluationRuns).toHaveBeenLastCalledWith(false);
    });

    it('hides the evaluation runs toggle when no evaluations exist', () => {
        render(DatasetGridHeader, {
            props: { ...defaultProps, isImages: true, hasEvaluationRuns: false }
        });

        expect(screen.queryByTestId('toggle-evaluation-runs-button')).not.toBeInTheDocument();
    });

    it('shows the embeddings and evaluation runs labels at full width', () => {
        // Compaction is driven by GridHeader's overflow measurement (covered in
        // GridHeader.test.ts); jsdom reports zero widths, so the labels stay visible here.
        render(DatasetGridHeader, {
            props: {
                ...defaultProps,
                isImages: true,
                hasMediaWithEmbeddings: true
            }
        });

        expect(screen.getByText('Embeddings')).toBeInTheDocument();
        expect(screen.getByText('Evaluation')).toBeInTheDocument();
    });
});
