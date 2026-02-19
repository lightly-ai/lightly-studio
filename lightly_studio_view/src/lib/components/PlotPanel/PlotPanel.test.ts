import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import PlotPanel from './PlotPanel.svelte';
import { useEmbeddings } from '$lib/hooks/useEmbeddings/useEmbeddings';
import { writable, type Writable } from 'svelte/store';

let rangeSelectionStore: Writable<Array<{ x: number; y: number }> | null>;
let selectedSampleIdsStore: Writable<string[]>;
let imageFilterStore: Writable<Record<string, unknown>>;
let arrowDataStore: Writable<Record<string, unknown> | undefined>;

const mockSetShowPlot = vi.fn();
const mockSetRangeSelectionForcollection = vi.fn();
const mockUpdateSampleIds = vi.fn();

vi.mock('$app/state', () => ({
    page: {
        params: { collection_id: 'test-collection-id' },
        route: {
            id: '/datasets/[dataset_id]/[collection_type]/[collection_id]/samples'
        }
    }
}));

// Mock dependencies
vi.mock('embedding-atlas/svelte', () => ({
    EmbeddingView: class MockEmbeddingView {}
}));
vi.mock('$lib/hooks/useEmbeddings/useEmbeddings');
vi.mock('./useArrowData/useArrowData', () => ({
    useArrowData: () => ({
        data: arrowDataStore,
        error: writable(null)
    })
}));
vi.mock('./usePlotData/usePlotData', () => ({
    usePlotData: () => ({
        data: writable(undefined),
        selectedSampleIds: selectedSampleIdsStore,
        error: writable(undefined)
    })
}));
vi.mock('$lib/hooks/useVideoFilters/useVideoFilters', () => ({
    useVideoFilters: () => ({
        videoFilter: writable(null),
        updateSampleIds: vi.fn()
    })
}));
vi.mock('$lib/hooks/useImageFilters/useImageFilters', () => ({
    useImageFilters: () => ({
        filterParams: writable({ mode: 'normal', filters: {} }),
        imageFilter: imageFilterStore,
        updateFilterParams: vi.fn(),
        updateSampleIds: mockUpdateSampleIds
    })
}));

vi.mock('$lib/hooks/useGlobalStorage', () => {
    return {
        useGlobalStorage: () => ({
            setShowPlot: mockSetShowPlot,
            getRangeSelection: vi.fn(() => rangeSelectionStore),
            setRangeSelectionForcollection: mockSetRangeSelectionForcollection
        })
    };
});

describe('PlotPanel.svelte', () => {
    beforeEach(() => {
        vi.resetAllMocks();
        rangeSelectionStore = writable(null);
        selectedSampleIdsStore = writable([]);
        imageFilterStore = writable({ sample_filter: { sample_ids: [] } });
        arrowDataStore = writable(undefined);
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

    it('should clear selection when pressing Escape', async () => {
        rangeSelectionStore = writable([
            { x: 0, y: 0 },
            { x: 1, y: 0 },
            { x: 1, y: 1 },
            { x: 0, y: 1 }
        ]);
        (useEmbeddings as vi.Mock).mockReturnValue(
            writable({
                isError: false,
                error: null,
                isLoading: true,
                data: null
            })
        );

        render(PlotPanel);
        await fireEvent.keyDown(window, { key: 'Escape' });

        expect(mockSetRangeSelectionForcollection).toHaveBeenCalledWith('test-collection-id', null);
        expect(mockUpdateSampleIds).toHaveBeenCalledWith([]);
    });

    it('should clear range selection geometry after applying mouse selection', async () => {
        rangeSelectionStore = writable([
            { x: 0, y: 0 },
            { x: 1, y: 0 },
            { x: 1, y: 1 },
            { x: 0, y: 1 }
        ]);
        selectedSampleIdsStore = writable(['sample-1']);
        (useEmbeddings as vi.Mock).mockReturnValue(
            writable({
                isError: false,
                error: null,
                isLoading: true,
                data: null
            })
        );

        render(PlotPanel);
        await fireEvent.mouseUp(window);

        expect(mockUpdateSampleIds).toHaveBeenCalledWith(['sample-1']);
        expect(mockSetRangeSelectionForcollection).toHaveBeenCalledWith('test-collection-id', null);
    });

    it('should clear embedding selection when base filters change', async () => {
        rangeSelectionStore = writable([
            { x: 0, y: 0 },
            { x: 1, y: 0 },
            { x: 1, y: 1 },
            { x: 0, y: 1 }
        ]);
        (useEmbeddings as vi.Mock).mockReturnValue(
            writable({
                isError: false,
                error: null,
                isLoading: true,
                data: null
            })
        );

        render(PlotPanel);

        imageFilterStore.set({
            sample_filter: {
                sample_ids: [],
                annotation_label_ids: ['dog']
            }
        });

        await waitFor(() => {
            expect(mockSetRangeSelectionForcollection).toHaveBeenCalledWith(
                'test-collection-id',
                null
            );
            expect(mockUpdateSampleIds).toHaveBeenCalledWith([]);
        });
    });

    it('should clear sample_ids when selecting all selectable points', async () => {
        rangeSelectionStore = writable([
            { x: 0, y: 0 },
            { x: 1, y: 0 },
            { x: 1, y: 1 },
            { x: 0, y: 1 }
        ]);
        selectedSampleIdsStore = writable(['sample-1', 'sample-2']);
        imageFilterStore = writable({ sample_filter: { sample_ids: ['stale-id'] } });
        arrowDataStore = writable({
            x: new Float32Array([1, 2, 3]),
            y: new Float32Array([1, 2, 3]),
            fulfils_filter: new Uint8Array([1, 1, 0]),
            sample_id: ['sample-1', 'sample-2', 'sample-3']
        });
        (useEmbeddings as vi.Mock).mockReturnValue(
            writable({
                isError: false,
                error: null,
                isLoading: true,
                data: null
            })
        );

        render(PlotPanel);
        await fireEvent.mouseUp(window);

        expect(mockUpdateSampleIds).toHaveBeenCalledWith([]);
        expect(mockUpdateSampleIds).not.toHaveBeenCalledWith(['sample-1', 'sample-2']);
        expect(mockSetRangeSelectionForcollection).toHaveBeenCalledWith('test-collection-id', null);
    });
});
