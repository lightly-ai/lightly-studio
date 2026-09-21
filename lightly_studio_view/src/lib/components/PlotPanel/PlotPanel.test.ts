import { fireEvent, render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import PlotPanel from './PlotPanel.svelte';
import { useEmbeddings } from '$lib/hooks/useEmbeddings/useEmbeddings';
import { get, writable, type Writable } from 'svelte/store';
import {
    clearAnnotationPlotSelection,
    useAnnotationPlotSelection
} from '$lib/hooks/useEmbeddingFilter/useEmbeddingFilterForAnnotations';
import { tick } from 'svelte';
import { usePlotColorByType } from './PlotColorByPopover/usePlotColorByType/usePlotColorByType';
import { EXCLUDED_BY_FILTERS_CATEGORY, INCLUDED_BY_FILTERS_CATEGORY } from './plotCategories';

let rangeSelectionStore: Writable<Array<{ x: number; y: number }> | null>;
let selectedSampleIdsStore: Writable<string[]>;
let imageFilterStore: Writable<Record<string, unknown>>;
let arrowDataStore: Writable<Record<string, unknown> | undefined>;
let colorLegendStore: Writable<Map<number, string>>;
let metadataInfoStore: Writable<Array<{ name: string; type: string }>>;

const mockResetCategoryVisibility = vi.fn();

const tagsStore = writable([
    { tag_id: 'tag-a', name: 'alpha', kind: 'sample' },
    { tag_id: 'tag-b', name: 'beta', kind: 'sample' }
]);

const mockSetShowEmbeddingPlot = vi.fn();
const mockSetRangeSelectionForCollection = vi.fn();
const mockUpdateSampleIds = vi.fn();
const mockUpdateEmbeddingRegion = vi.fn();
const mockSetPlotSelectionCount = vi.fn();
const mockClearPlotSelectionCount = vi.fn();

class ResizeObserverMock {
    observe() {}
    disconnect() {}
}

const originalHasPointerCapture = Element.prototype.hasPointerCapture;
const originalSetPointerCapture = Element.prototype.setPointerCapture;
const originalReleasePointerCapture = Element.prototype.releasePointerCapture;
const originalScrollIntoView = Element.prototype.scrollIntoView;
const originalResizeObserver = globalThis.ResizeObserver;

vi.stubGlobal('ResizeObserver', ResizeObserverMock);

const IMAGES_ROUTE = '/datasets/[dataset_id]/[collection_type]/[collection_id]/images';
const ANNOTATIONS_ROUTE = '/datasets/[dataset_id]/[collection_type]/[collection_id]/annotations';
// Route is read per-render, so tests set `routeState.id` before rendering to pick a grid type.
const routeState = vi.hoisted(() => ({ id: '' }));

vi.mock('$app/state', () => ({
    page: {
        params: { collection_id: 'test-collection-id' },
        route: routeState
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
        colorLegend: colorLegendStore,
        error: writable(null)
    })
}));
vi.mock('./useCategoryVisibility/useCategoryVisibility', () => ({
    useCategoryVisibility: () => ({
        hiddenCategories: writable(new Set<number>()),
        toggleCategoryVisibility: vi.fn(),
        focusCategoryVisibility: vi.fn(),
        resetCategoryVisibility: mockResetCategoryVisibility
    })
}));
const usePlotDataSpy = vi.hoisted(() => vi.fn());
vi.mock('./usePlotData/usePlotData', () => ({
    usePlotData: (args: unknown) => {
        usePlotDataSpy(args);
        return {
            data: writable(undefined),
            selectedSampleIds: selectedSampleIdsStore,
            error: writable(undefined)
        };
    }
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
        updateSampleIds: mockUpdateSampleIds,
        updateEmbeddingRegion: mockUpdateEmbeddingRegion
    })
}));
vi.mock('$lib/hooks/useEmbeddingFilter/useEmbeddingPlotSelection', () => ({
    setPlotSelectionCount: (...args: [string, number]) => mockSetPlotSelectionCount(...args),
    clearPlotSelectionCount: (...args: [string]) => mockClearPlotSelectionCount(...args)
}));
vi.mock('$lib/hooks/useMetadataFilters/useMetadataFilters', () => ({
    useMetadataFilters: () => ({
        metadataInfo: metadataInfoStore
    })
}));
vi.mock('$lib/hooks/useTags/useTags', () => ({
    useTags: () => ({
        tags: tagsStore
    })
}));
vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: () => ({ data: [] })
}));
vi.mock('$lib/hooks/useAnnotationsFilter/useAnnotationsFilter', () => ({
    useSelectedAnnotationsFilter: () => ({
        annotationFilter: writable(undefined)
    })
}));

vi.mock('$lib/hooks/useGlobalStorage', () => {
    return {
        useGlobalStorage: () => ({
            setShowEmbeddingPlot: mockSetShowEmbeddingPlot,
            getRangeSelection: vi.fn(() => rangeSelectionStore),
            setRangeSelectionForCollection: mockSetRangeSelectionForCollection
        })
    };
});

describe('PlotPanel.svelte', () => {
    beforeAll(() => {
        Element.prototype.hasPointerCapture = vi.fn(() => false);
        Element.prototype.setPointerCapture = vi.fn();
        Element.prototype.releasePointerCapture = vi.fn();
        Element.prototype.scrollIntoView = vi.fn();
    });

    afterAll(() => {
        Element.prototype.hasPointerCapture = originalHasPointerCapture;
        Element.prototype.setPointerCapture = originalSetPointerCapture;
        Element.prototype.releasePointerCapture = originalReleasePointerCapture;
        Element.prototype.scrollIntoView = originalScrollIntoView;
        vi.stubGlobal('ResizeObserver', originalResizeObserver);
    });

    beforeEach(() => {
        vi.resetAllMocks();
        vi.stubGlobal('ResizeObserver', ResizeObserverMock);
        routeState.id = IMAGES_ROUTE;
        clearAnnotationPlotSelection('test-collection-id');
        usePlotColorByType('test-collection-id').clearSelectedColorByType();
        rangeSelectionStore = writable(null);
        selectedSampleIdsStore = writable([]);
        imageFilterStore = writable({ sample_filter: { sample_ids: [] } });
        arrowDataStore = writable(undefined);
        colorLegendStore = writable(new Map());
        metadataInfoStore = writable([{ name: 'split', type: 'string' }]);
        tagsStore.set([
            { tag_id: 'tag-a', name: 'alpha', kind: 'sample' },
            { tag_id: 'tag-b', name: 'beta', kind: 'sample' }
        ]);
        (useEmbeddings as vi.Mock).mockReturnValue(
            writable({
                isError: false,
                error: null,
                isLoading: false,
                data: new Blob()
            })
        );
    });

    it('should display an error message when useEmbeddings returns an error object', async () => {
        const mockError: Error = { name: 'TestError', message: 'Test error from object' };
        (useEmbeddings as vi.Mock).mockReturnValue({
            isError: true,
            error: mockError,
            isLoading: false,
            data: null
        });

        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });

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
        (useEmbeddings as vi.Mock).mockReturnValue({
            isError: false,
            error: null,
            isLoading: true,
            data: null
        });

        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });
        await fireEvent.keyDown(window, { key: 'Escape' });

        expect(mockSetRangeSelectionForCollection).toHaveBeenCalledWith('test-collection-id', null);
        // Images clear the region geometry, not a sample-id list.
        expect(mockUpdateEmbeddingRegion).toHaveBeenCalledWith(null);
        expect(mockClearPlotSelectionCount).toHaveBeenCalledWith('test-collection-id');
        expect(mockUpdateSampleIds).not.toHaveBeenCalled();
    });

    it('should send the lasso as region geometry after applying mouse selection', async () => {
        const polygon = [
            { x: 0, y: 0 },
            { x: 1, y: 0 },
            { x: 1, y: 1 },
            { x: 0, y: 1 }
        ];
        rangeSelectionStore = writable(polygon);
        selectedSampleIdsStore = writable(['sample-1']);
        (useEmbeddings as vi.Mock).mockReturnValue({
            isError: false,
            error: null,
            isLoading: true,
            data: null
        });

        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });
        await fireEvent.mouseUp(window);

        expect(mockUpdateEmbeddingRegion).toHaveBeenCalledWith({ polygon });
        expect(mockSetPlotSelectionCount).toHaveBeenCalledWith('test-collection-id', 1);
        expect(mockUpdateSampleIds).not.toHaveBeenCalled();
        expect(mockSetRangeSelectionForCollection).toHaveBeenCalledWith('test-collection-id', null);
    });

    it('should not clear embedding selection when base filters change', async () => {
        rangeSelectionStore = writable([
            { x: 0, y: 0 },
            { x: 1, y: 0 },
            { x: 1, y: 1 },
            { x: 0, y: 1 }
        ]);
        (useEmbeddings as vi.Mock).mockReturnValue({
            isError: false,
            error: null,
            isLoading: true,
            data: null
        });

        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });

        imageFilterStore.set({
            sample_filter: {
                sample_ids: [],
                annotations_filter: {
                    annotation_label_ids: ['dog']
                }
            }
        });

        await tick();
        expect(mockSetRangeSelectionForCollection).not.toHaveBeenCalled();
        expect(mockUpdateSampleIds).not.toHaveBeenCalled();
        expect(mockUpdateEmbeddingRegion).not.toHaveBeenCalled();
    });

    it('should clear the region when selecting all selectable points', async () => {
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
            color_categories: [[3], [3], []],
            sample_id: ['sample-1', 'sample-2', 'sample-3']
        });

        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });
        await fireEvent.mouseUp(window);

        // Selecting every selectable point is equivalent to no filter, so the region is cleared.
        expect(mockUpdateEmbeddingRegion).toHaveBeenCalledWith(null);
        expect(mockClearPlotSelectionCount).toHaveBeenCalledWith('test-collection-id');
        expect(mockSetPlotSelectionCount).not.toHaveBeenCalled();
        expect(mockSetRangeSelectionForCollection).toHaveBeenCalledWith('test-collection-id', null);
    });

    it('saves the lasso to the annotation region store on the annotations route', async () => {
        routeState.id = ANNOTATIONS_ROUTE;
        const polygon = [
            { x: 0, y: 0 },
            { x: 1, y: 0 },
            { x: 1, y: 1 },
            { x: 0, y: 1 }
        ];
        rangeSelectionStore = writable(polygon);
        selectedSampleIdsStore = writable(['annotation-1']);
        (useEmbeddings as vi.Mock).mockReturnValue({
            isError: false,
            error: null,
            isLoading: true,
            data: null
        });

        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });
        await fireEvent.mouseUp(window);

        // Annotations have no filter store, so the geometry goes to the shared region store.
        expect(get(useAnnotationPlotSelection().annotationPlotRegion)).toEqual({ polygon });
        expect(mockSetPlotSelectionCount).toHaveBeenCalledWith('test-collection-id', 1);
        // The image filter path must stay untouched on the annotations route.
        expect(mockUpdateEmbeddingRegion).not.toHaveBeenCalled();
        expect(mockSetRangeSelectionForCollection).toHaveBeenCalledWith('test-collection-id', null);
    });

    it('highlights the committed annotation region after the live selection clears', async () => {
        routeState.id = ANNOTATIONS_ROUTE;
        const polygon = [
            { x: 0, y: 0 },
            { x: 1, y: 0 },
            { x: 1, y: 1 },
            { x: 0, y: 1 }
        ];
        // The selection is already committed: no live rangeSelection, region in the shared store.
        rangeSelectionStore = writable(null);
        useAnnotationPlotSelection().saveRegion({ polygon });

        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });
        await tick();

        // The plot must re-derive the highlight from the committed region so the selected
        // annotations stay highlighted instead of collapsing to "all included".
        const lastArgs = usePlotDataSpy.mock.calls.at(-1)?.[0];
        expect(lastArgs?.highlightRegion).toEqual(polygon);
    });

    it('passes derived colorBy to useEmbeddings when a metadata field is selected', async () => {
        const user = userEvent.setup();

        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });

        expect(useEmbeddings).toHaveBeenLastCalledWith(
            'test-collection-id',
            expect.anything(),
            null
        );

        await user.click(screen.getByTestId('plot-color-by-button'));
        await user.click(await screen.findByRole('option', { name: 'metadata.split' }));
        await tick();

        expect(useEmbeddings).toHaveBeenLastCalledWith('test-collection-id', expect.anything(), {
            type: 'metadata_field',
            key: 'split'
        });
    });

    it('passes tag_ids colorBy to useEmbeddings when tags type is selected', async () => {
        const user = userEvent.setup();

        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });

        await user.click(screen.getByTestId('plot-color-by-button'));
        await user.click(await screen.findByRole('option', { name: 'tags' }));
        await tick();

        expect(useEmbeddings).toHaveBeenLastCalledWith('test-collection-id', expect.anything(), {
            type: 'tag',
            tag_ids: ['tag-a', 'tag-b']
        });
    });

    it('resets remapped categories when the legend changes but preserves the reserved rows', async () => {
        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });
        await tick();

        // Ignore the reset that fires on mount; assert the one triggered by the legend change.
        mockResetCategoryVisibility.mockClear();
        colorLegendStore.set(new Map([[3, 'dog']]));
        await tick();

        // Reserved rows are stable by index, so they must survive a legend refresh.
        expect(mockResetCategoryVisibility).toHaveBeenCalledWith([
            EXCLUDED_BY_FILTERS_CATEGORY,
            INCLUDED_BY_FILTERS_CATEGORY
        ]);
    });

    it('drops the "Included by filters / No category" row when the color-by mode changes', async () => {
        const user = userEvent.setup();
        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });
        await tick();

        // Ignore the resets from mount; assert the one triggered by the color-by change.
        mockResetCategoryVisibility.mockClear();
        await user.click(screen.getByTestId('plot-color-by-button'));
        await user.click(await screen.findByRole('option', { name: 'metadata.split' }));
        await tick();

        // INCLUDED is relabeled when the color-by mode flips, so its hidden state must not carry
        // over (it would otherwise hide every point in the relabeled slot). Only EXCLUDED survives.
        expect(mockResetCategoryVisibility).toHaveBeenLastCalledWith([
            EXCLUDED_BY_FILTERS_CATEGORY
        ]);
    });
});
