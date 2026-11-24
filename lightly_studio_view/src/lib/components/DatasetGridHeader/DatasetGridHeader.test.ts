import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import { readable, writable } from 'svelte/store';
import '@testing-library/jest-dom';
import type { SlotRegistry } from '$lib/extensions';
import { registry } from '$lib/extensions/registry';
import ExtensionSlotTestItem from '$lib/extensions/ExtensionSlot/ExtensionSlotTestItem.test.svelte';

vi.mock('$lib/hooks/useGlobalStorage', () => {
    return {
        useGlobalStorage: () => ({
            activePanel: writable('none'),
            sampleSize: writable({ width: 4, height: 4 }),
            updateSampleSize: vi.fn()
        })
    };
});

vi.mock('$lib/hooks/useImageOrderBy/useImageOrderBy', () => ({
    useImageOrderBy: () => ({
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

vi.mock('$lib/extensions/registry', () => ({ registry: {} as SlotRegistry }));

import DatasetGridHeader from './DatasetGridHeader.svelte';

const defaultProps = {
    collectionId: 'col1',
    canSelectAll: false,
    isSelectionActive: false,
    isImages: false,
    isVideos: false,
    isAnnotations: false,
    hasMediaWithEmbeddings: false,
    collectionDatasetId: 'dataset-1',
    onSelectAll: vi.fn().mockResolvedValue(undefined),
    onDeselectAll: vi.fn(),
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
        defaultProps.onSelectAll.mockClear();
        defaultProps.onDeselectAll.mockClear();
        delete registry['dataset.toolbar'];
    });

    it('renders a registered toolbar component with the dataset and collection ids', () => {
        registry['dataset.toolbar'] = [ExtensionSlotTestItem];

        render(DatasetGridHeader, { props: defaultProps });

        expect(screen.getByTestId('registered')).toHaveTextContent('dataset-1/col1');
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

    it('calls onDeselectAll when the select-all checkbox is toggled off', async () => {
        render(DatasetGridHeader, {
            props: { ...defaultProps, canSelectAll: true, isSelectionActive: true }
        });

        const checkbox = screen.getByTestId('select-all-button');
        await fireEvent.click(checkbox);
        expect(defaultProps.onDeselectAll).toHaveBeenCalledTimes(1);
        expect(defaultProps.onSelectAll).not.toHaveBeenCalled();
    });

    it('renders the ImageOrderBy control only for image collections', () => {
        const { unmount } = render(DatasetGridHeader, {
            props: { ...defaultProps, isImages: true }
        });
        expect(screen.getByTestId('sort-by-trigger')).toBeInTheDocument();
        unmount();

        render(DatasetGridHeader, { props: { ...defaultProps } });
        expect(screen.queryByTestId('sort-by-trigger')).not.toBeInTheDocument();
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
