import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import { readable, writable } from 'svelte/store';
import '@testing-library/jest-dom';

vi.mock('$lib/hooks/useGlobalStorage', () => {
    const showPlot = writable<boolean>(false);
    const setShowPlot = vi.fn((value: boolean) => showPlot.set(value));
    return {
        useGlobalStorage: () => ({
            showPlot,
            setShowPlot,
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
        toggleDirection: vi.fn()
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
    hasMediaWithEmbeddings: false,
    datasetId: 'dataset-1',
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
        storage.showPlot.set(false);
        (storage.setShowPlot as ReturnType<typeof vi.fn>).mockClear();
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
        expect(screen.getByText('Show Embeddings')).toBeInTheDocument();
    });

    it('hides the embeddings toggle when media has no embeddings', () => {
        render(DatasetGridHeader, {
            props: { ...defaultProps, isImages: true, hasMediaWithEmbeddings: false }
        });

        expect(screen.queryByTestId('toggle-plot-button')).not.toBeInTheDocument();
    });

    it('toggles the plot store when the embeddings button is clicked', async () => {
        const { setShowPlot } = useGlobalStorage();

        render(DatasetGridHeader, {
            props: { ...defaultProps, isImages: true, hasMediaWithEmbeddings: true }
        });

        const toggle = screen.getByTestId('toggle-plot-button');
        await fireEvent.click(toggle);
        expect(setShowPlot).toHaveBeenLastCalledWith(true);

        await fireEvent.click(toggle);
        expect(setShowPlot).toHaveBeenLastCalledWith(false);
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
});
