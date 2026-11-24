import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient } from '@tanstack/svelte-query';
import { transferableAbortController } from 'node:util';
import { client } from '$lib/api/lightly_studio_local/client.gen';
import UseVideosHarness from '$lib/hooks/useVideos/UseVideosHarness.svelte';
import type { useVideoFilters } from '$lib/hooks/useVideoFilters/useVideoFilters';
import PlotPanel from './PlotPanel.svelte';
import { useEmbeddings } from '$lib/hooks/useEmbeddings/useEmbeddings';
import { fromStore, get, writable, type Writable } from 'svelte/store';
import {
    clearAnnotationPlotSelection,
    useAnnotationPlotSelection
} from '$lib/hooks/useEmbeddingFilter/useEmbeddingFilterForAnnotations';
import { tick } from 'svelte';
import { usePlotColorByType } from './PlotColorByPopover/usePlotColorByType/usePlotColorByType';
import { EXCLUDED_BY_FILTERS_CATEGORY } from './plotCategories';
import { clearPlotLayout } from './usePlotLayout/usePlotLayout';

let rangeSelectionStore: Writable<Array<{ x: number; y: number }> | null>;
let selectedSampleIdsStore: Writable<string[]>;
let imageFilterStore: Writable<Record<string, unknown>>;
let videoFilterStore: Writable<{
    sample_filter?: {
        sample_ids?: string[];
        embedding_region?: { polygon: { x: number; y: number }[] };
    };
} | null>;
let actualVideoFilters: ReturnType<typeof useVideoFilters> | null = null;
const originalClientConfig = client.getConfig();
const originalAbortController = globalThis.AbortController;
let plotDataStore: Writable<{ x: Float32Array; y: Float32Array; category: Uint8Array } | undefined>;
let hiddenCategoriesStore: Writable<Set<number>>;
let metadataInfoStore: Writable<Array<{ name: string; type: string }>>;
let annotationLabelsQuery: { data?: unknown[]; isSuccess: boolean; isError: boolean };

const mockClearForColorByMode = vi.fn();

const tagsStore = writable([
    { tag_id: 'tag-a', name: 'alpha' },
    { tag_id: 'tag-b', name: 'beta' }
]);

const mockSetShowEmbeddingPlot = vi.fn();
const mockSetRangeSelectionForCollection = vi.fn();
const mockUpdatePlotSelection = vi.fn();
const NO_PLOT_SELECTION = vi.hoisted(() => ({ embeddingRegion: null, sampleIds: [] }));
const mockSetPlotSelectionCount = vi.fn();
const mockClearPlotSelectionCount = vi.fn();
let plotSelectionCountStore: Writable<number>;

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
const VIDEOS_ROUTE = '/datasets/[dataset_id]/[collection_type]/[collection_id]/videos';
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
vi.mock('embedding-atlas/svelte', async () => ({
    EmbeddingView: (await import('./EmbeddingViewStub.test.svelte')).default
}));
vi.mock('$lib/hooks/useEmbeddings/useEmbeddings');
const mockEmbedTextAxes = vi.hoisted(() => vi.fn());
vi.mock('./PlotTextAxesInputs/embedTextAxes', () => ({ embedTextAxes: mockEmbedTextAxes }));
vi.mock('./useCategoryVisibility/useCategoryVisibility', () => ({
    useCategoryVisibility: () => ({
        hiddenCategories: hiddenCategoriesStore,
        toggleCategoryVisibility: vi.fn(),
        focusCategoryVisibility: vi.fn(),
        clearForColorByMode: mockClearForColorByMode
    })
}));
const usePlotDataSpy = vi.hoisted(() => vi.fn());
vi.mock('./usePlotData/usePlotData', () => ({
    usePlotData: (args: unknown) => {
        usePlotDataSpy(args);
        return {
            data: plotDataStore,
            selectedSampleIds: selectedSampleIdsStore,
            error: writable(undefined)
        };
    }
}));
vi.mock('$lib/hooks/useVideoFilters/useVideoFilters', () => ({
    useVideoFilters: () =>
        actualVideoFilters ?? {
            videoFilter: videoFilterStore,
            updatePlotSelection: (selection: {
                embeddingRegion: { polygon: { x: number; y: number }[] } | null;
            }) => {
                mockUpdatePlotSelection(selection);
                videoFilterStore.update((filter) => ({
                    ...filter,
                    sample_filter: {
                        ...filter?.sample_filter,
                        embedding_region: selection.embeddingRegion ?? undefined
                    }
                }));
            }
        }
}));
vi.mock('$lib/hooks/useImageFilters/useImageFilters', () => ({
    useImageFilters: () => ({
        filterParams: writable({ mode: 'normal', filters: {} }),
        imageFilter: imageFilterStore,
        updateFilterParams: vi.fn(),
        updatePlotSelection: mockUpdatePlotSelection
    })
}));
vi.mock('$lib/hooks/useEmbeddingFilter/useEmbeddingPlotSelection', () => ({
    setPlotSelectionCount: (...args: [string, number]) => mockSetPlotSelectionCount(...args),
    clearPlotSelectionCount: (...args: [string]) => mockClearPlotSelectionCount(...args),
    getPlotSelectionCount: () => plotSelectionCountStore,
    EMPTY_PLOT_SELECTION: NO_PLOT_SELECTION
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
    useAnnotationLabels: () => annotationLabelsQuery
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

const SQUARE_POLYGON = [
    { x: 0, y: 0 },
    { x: 1, y: 0 },
    { x: 1, y: 1 },
    { x: 0, y: 1 }
];
const TEXT_LAYOUT_AXES = { x: [1, 0, 0], y: [0, 1, 0] };

const openAxesEditor = async (user: ReturnType<typeof userEvent.setup>) => {
    await user.click(screen.getByRole('button', { name: 'Define axes' }));
};

// Applies four axis texts in the axes editor.
const commitTextAxes = async (user: ReturnType<typeof userEvent.setup>) => {
    await openAxesEditor(user);
    await user.type(screen.getByLabelText('Left'), 'young');
    await user.type(screen.getByLabelText('Right'), 'old');
    await user.type(screen.getByLabelText('Bottom'), 'sad');
    await user.type(screen.getByLabelText('Top'), 'happy');
    await user.click(screen.getByRole('button', { name: 'Apply axes' }));
};

// The plot reads the embeddings query result reactively, so a test can change it after render.
const mockEmbeddingsQuery = (initialResult: Record<string, unknown>) => {
    const result = writable(initialResult);
    const currentResult = fromStore(result);
    const query = new Proxy({}, { get: (_, key: string) => currentResult.current[key] });
    vi.mocked(useEmbeddings).mockReturnValue(query as ReturnType<typeof useEmbeddings>);
    return result;
};

// useEmbeddings is called once with a getter; the getter returns the current request.
const lastEmbeddingsParams = () => vi.mocked(useEmbeddings).mock.lastCall![0]();

describe('PlotPanel.svelte', () => {
    afterEach(() => {
        client.setConfig({ ...originalClientConfig, fetch: originalClientConfig.fetch });
        vi.stubGlobal('AbortController', originalAbortController);
        vi.restoreAllMocks();
    });

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
        actualVideoFilters = null;
        clearAnnotationPlotSelection('test-collection-id');
        clearPlotLayout('test-collection-id');
        usePlotColorByType('test-collection-id').clearSelectedColorByType();
        rangeSelectionStore = writable(null);
        selectedSampleIdsStore = writable([]);
        plotSelectionCountStore = writable(0);
        imageFilterStore = writable({ sample_filter: { sample_ids: [] } });
        videoFilterStore = writable(null);
        plotDataStore = writable(undefined);
        hiddenCategoriesStore = writable(new Set<number>());
        metadataInfoStore = writable([{ name: 'split', type: 'string' }]);
        annotationLabelsQuery = { data: [], isSuccess: true, isError: false };
        tagsStore.set([
            { tag_id: 'tag-a', name: 'alpha' },
            { tag_id: 'tag-b', name: 'beta' }
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
        const mockError = new Error('Test error from object');
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
        expect(mockUpdatePlotSelection).toHaveBeenCalledWith(NO_PLOT_SELECTION);
        expect(mockClearPlotSelectionCount).toHaveBeenCalledWith('test-collection-id');
    });

    it('clears the video region and selection count when pressing Escape', async () => {
        routeState.id = VIDEOS_ROUTE;
        videoFilterStore = writable({
            sample_filter: { embedding_region: { polygon: [{ x: 0, y: 0 }] } }
        });
        (useEmbeddings as vi.Mock).mockReturnValue({
            isError: false,
            error: null,
            isLoading: true,
            data: null
        });

        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });
        await fireEvent.keyDown(window, { key: 'Escape' });

        expect(mockUpdatePlotSelection).toHaveBeenCalledWith(NO_PLOT_SELECTION);
        expect(mockClearPlotSelectionCount).toHaveBeenCalledWith('test-collection-id');
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

        expect(mockUpdatePlotSelection).toHaveBeenCalledWith({
            embeddingRegion: { polygon },
            sampleIds: []
        });
        expect(mockSetPlotSelectionCount).toHaveBeenCalledWith('test-collection-id', 1);
        expect(mockSetRangeSelectionForCollection).toHaveBeenCalledWith('test-collection-id', null);
    });

    it('saves and highlights video lassos as region geometry', async () => {
        routeState.id = VIDEOS_ROUTE;
        const polygon = [
            { x: 0, y: 0 },
            { x: 1, y: 0 },
            { x: 1, y: 1 },
            { x: 0, y: 1 }
        ];
        rangeSelectionStore = writable(polygon);
        selectedSampleIdsStore = writable(['video-1']);

        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });
        await fireEvent.mouseUp(window);

        expect(mockUpdatePlotSelection).toHaveBeenCalledWith({
            embeddingRegion: { polygon },
            sampleIds: []
        });
        expect(mockSetPlotSelectionCount).toHaveBeenCalledWith('test-collection-id', 1);
        expect(usePlotDataSpy.mock.calls.at(-1)?.[0].highlightRegion).toEqual(polygon);
    });

    it('keeps the video lasso request small for a large selection', async () => {
        routeState.id = VIDEOS_ROUTE;
        // Node's Request requires a native AbortSignal rather than jsdom's signal.
        vi.stubGlobal('AbortController', transferableAbortController().constructor);
        const { useVideoFilters } = await vi.importActual<
            typeof import('$lib/hooks/useVideoFilters/useVideoFilters')
        >('$lib/hooks/useVideoFilters/useVideoFilters');
        const videoFilters = useVideoFilters();
        actualVideoFilters = videoFilters;
        const requestBodies: string[] = [];
        client.setConfig({
            baseUrl: 'http://localhost:8001',
            fetch: async (input) => {
                const request = new Request(input);
                expect(request.method).toBe('POST');
                expect(new URL(request.url).pathname).toBe(
                    '/api/collections/test-collection-id/video/'
                );
                requestBodies.push(await request.text());
                return new Response(
                    JSON.stringify({ data: [], total_count: 0, nextCursor: null }),
                    {
                        headers: { 'Content-Type': 'application/json' }
                    }
                );
            }
        });
        const polygon = [
            { x: 0, y: 0 },
            { x: 1, y: 0 },
            { x: 1, y: 1 },
            { x: 0, y: 1 }
        ];
        const requestBodySizes: number[] = [];
        let oldIdListRequestBody = '';
        for (const selectionCount of [1, 5000]) {
            videoFilters.updateFilterParams({ collection_id: 'test-collection-id' });
            const selectedSampleIds = Array.from(
                { length: selectionCount },
                (_, index) => `video-${index}`
            );
            rangeSelectionStore = writable(polygon);
            selectedSampleIdsStore = writable(selectedSampleIds);

            const { unmount } = render(PlotPanel, {
                props: { collectionId: 'test-collection-id' }
            });
            await fireEvent.mouseUp(window);

            const queryClient = new QueryClient({
                defaultOptions: { queries: { retry: false, gcTime: 0 } }
            });
            let requestError: unknown = null;
            const videos = render(UseVideosHarness, {
                queryClient,
                onError: (error) => {
                    requestError = error;
                },
                getParams: () => ({
                    collection_id: 'test-collection-id',
                    filter: get(videoFilters.videoFilter) ?? { filter_type: 'video' }
                })
            });
            await waitFor(() => {
                expect(requestError).toBeNull();
                expect(requestBodies).toHaveLength(requestBodySizes.length + 1);
            });
            const requestBody = requestBodies[requestBodySizes.length];
            const body = JSON.parse(requestBody);
            expect(body.filter.filter_type).toBe('video');
            expect(body.filter.sample_filter).toEqual({
                embedding_region: { polygon }
            });
            requestBodySizes.push(new Blob([requestBody]).size);
            oldIdListRequestBody = JSON.stringify({
                ...body,
                filter: { ...body.filter, sample_filter: { sample_ids: selectedSampleIds } }
            });
            videos.unmount();
            queryClient.clear();
            unmount();
        }

        expect(new Set(requestBodySizes).size).toBe(1);
        expect(requestBodySizes[0]).toBeLessThan(new Blob([oldIdListRequestBody]).size / 10);
        expect(mockSetPlotSelectionCount).toHaveBeenCalledWith('test-collection-id', 5000);
    });

    it.each([
        { selectedSampleIds: [], fulfillsFilter: [1, 1] },
        { selectedSampleIds: ['video-1', 'video-2'], fulfillsFilter: [1, 1] }
    ])('clears a video region when the lasso selects nothing or everything', async (selection) => {
        routeState.id = VIDEOS_ROUTE;
        videoFilterStore = writable({
            sample_filter: { embedding_region: { polygon: [{ x: 0, y: 0 }] } }
        });
        rangeSelectionStore = writable([
            { x: 0, y: 0 },
            { x: 1, y: 0 },
            { x: 1, y: 1 },
            { x: 0, y: 1 }
        ]);
        selectedSampleIdsStore = writable(selection.selectedSampleIds);
        mockEmbeddingsQuery({
            data: { columns: { fulfils_filter: new Uint8Array(selection.fulfillsFilter) } }
        });

        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });
        await fireEvent.mouseUp(window);

        expect(mockUpdatePlotSelection).toHaveBeenCalledWith(NO_PLOT_SELECTION);
        expect(mockSetPlotSelectionCount).not.toHaveBeenCalled();
        expect(mockClearPlotSelectionCount).toHaveBeenCalledWith('test-collection-id');
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
        expect(mockUpdatePlotSelection).not.toHaveBeenCalled();
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
        mockEmbeddingsQuery({
            data: {
                columns: {
                    x: new Float32Array([1, 2, 3]),
                    y: new Float32Array([1, 2, 3]),
                    fulfils_filter: new Uint8Array([1, 1, 0]),
                    color_categories: [[3], [3], []],
                    sample_id: ['sample-1', 'sample-2', 'sample-3']
                }
            }
        });

        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });
        await fireEvent.mouseUp(window);

        // Selecting every selectable point is equivalent to no filter, so the region is cleared.
        expect(mockUpdatePlotSelection).toHaveBeenCalledWith(NO_PLOT_SELECTION);
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
        expect(mockUpdatePlotSelection).not.toHaveBeenCalled();
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
        useAnnotationPlotSelection().savePlotSelection({
            embeddingRegion: { polygon },
            sampleIds: []
        });

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

        expect(lastEmbeddingsParams()).toMatchObject({
            collectionId: 'test-collection-id',
            colorBy: null,
            axes: null
        });

        await user.click(screen.getByTestId('plot-color-by-button'));
        await user.click(await screen.findByRole('option', { name: 'metadata.split' }));
        await tick();

        expect(lastEmbeddingsParams()).toMatchObject({
            collectionId: 'test-collection-id',
            colorBy: { type: 'metadata_field', key: 'split' },
            axes: null
        });
    });

    it('passes tag_ids colorBy to useEmbeddings when tags type is selected', async () => {
        const user = userEvent.setup();

        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });

        await user.click(screen.getByTestId('plot-color-by-button'));
        await user.click(await screen.findByRole('option', { name: 'tags' }));
        await tick();

        expect(lastEmbeddingsParams()).toMatchObject({
            collectionId: 'test-collection-id',
            colorBy: { type: 'tag', tag_ids: ['tag-a', 'tag-b'] },
            axes: null
        });
    });

    it('fetches without labels when the annotation labels fail to load', async () => {
        annotationLabelsQuery = { data: undefined, isSuccess: false, isError: true };
        usePlotColorByType('test-collection-id').setSelectedColorByType('annotation_label');

        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });
        await tick();

        expect(lastEmbeddingsParams().colorBy).toEqual({
            type: 'annotation',
            annotation_label_ids: []
        });
    });

    it('lays the plot out on the committed text axes and saves them with the lasso region', async () => {
        const user = userEvent.setup();
        mockEmbedTextAxes.mockResolvedValue(TEXT_LAYOUT_AXES);
        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });

        await commitTextAxes(user);

        expect(mockEmbedTextAxes).toHaveBeenCalledWith('test-collection-id', {
            x: { negative: 'young', positive: 'old' },
            y: { negative: 'sad', positive: 'happy' }
        });
        await vi.waitFor(() =>
            expect(lastEmbeddingsParams()).toMatchObject({
                collectionId: 'test-collection-id',
                colorBy: null,
                axes: TEXT_LAYOUT_AXES
            })
        );

        selectedSampleIdsStore.set(['sample-1']);
        rangeSelectionStore.set(SQUARE_POLYGON);
        await fireEvent.mouseUp(window);

        // The server resolves the region on the same axes as the plot.
        expect(mockUpdatePlotSelection).toHaveBeenLastCalledWith({
            embeddingRegion: { polygon: SQUARE_POLYGON, axes: TEXT_LAYOUT_AXES },
            sampleIds: []
        });
    });

    it('shows a plot filter chip on the plot while a region is selected', async () => {
        const user = userEvent.setup();
        vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(
            () => new DOMRect(0, 0, 400, 400)
        );
        const point = new Float32Array([0]);
        plotDataStore.set({ x: point, y: point, category: new Uint8Array([0]) });

        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });
        await screen.findByTestId('plot-viewport');
        expect(screen.queryByTestId('plot-selection-chip')).not.toBeInTheDocument();

        plotSelectionCountStore.set(3);
        expect(await screen.findByTestId('plot-selection-chip')).toHaveTextContent(/^3 images$/);

        mockClearPlotSelectionCount.mockImplementationOnce(() => plotSelectionCountStore.set(0));
        await user.click(screen.getByRole('button', { name: 'Clear plot filter' }));
        expect(mockUpdatePlotSelection).toHaveBeenCalledWith(NO_PLOT_SELECTION);
        await waitFor(() =>
            expect(screen.queryByTestId('plot-selection-chip')).not.toBeInTheDocument()
        );
    });

    it('treats a short shift-drag as a click and keeps the picks', async () => {
        vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(
            () => new DOMRect(0, 0, 400, 400)
        );
        const point = new Float32Array([0]);
        plotDataStore.set({ x: point, y: point, category: new Uint8Array([0]) });
        imageFilterStore = writable({ sample_filter: { sample_ids: ['sample-1'] } });
        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });
        const plot = await screen.findByTestId('plot-viewport');
        mockClearPlotSelectionCount.mockClear();

        // jsdom has no PointerEvent, so fireEvent.pointerDown drops the modifier keys.
        plot.dispatchEvent(
            new MouseEvent('pointerdown', { bubbles: true, shiftKey: true, clientX: 10 })
        );
        rangeSelectionStore.set(SQUARE_POLYGON);
        await fireEvent.mouseUp(window, { clientX: 14 });

        expect(mockSetRangeSelectionForCollection).toHaveBeenCalledWith('test-collection-id', null);
        expect(mockUpdatePlotSelection).not.toHaveBeenCalled();
        expect(mockClearPlotSelectionCount).not.toHaveBeenCalled();
    });

    it('uses the text-axis viewport after resetting a user pan', async () => {
        const user = userEvent.setup();
        const viewport = () => screen.getByTestId('plot-viewport');
        const defaultViewport = JSON.stringify({ x: 0, y: 0, scale: 5 });
        vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(
            () => new DOMRect(0, 0, 400, 400)
        );
        const point = new Float32Array([0]);
        plotDataStore.set({ x: point, y: point, category: new Uint8Array([0]) });
        mockEmbedTextAxes.mockResolvedValue(TEXT_LAYOUT_AXES);

        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });
        // PaCMAP has no default viewport: Embedding Atlas fits the view to the data.
        expect(await screen.findByTestId('plot-viewport')).toHaveTextContent('null');

        await commitTextAxes(user);
        expect(viewport()).toHaveTextContent(defaultViewport);

        await user.click(screen.getByRole('button', { name: 'Pan plot' }));
        expect(viewport()).toHaveTextContent(JSON.stringify({ x: 1, y: 1, scale: 3 }));

        await user.click(screen.getByTestId('plot-reset-zoom-button'));
        expect(viewport()).toHaveTextContent(defaultViewport);
    });

    it('preserves the plot and selection while defining or canceling axes', async () => {
        const user = userEvent.setup();
        imageFilterStore = writable({
            sample_filter: { sample_ids: [], embedding_region: { polygon: SQUARE_POLYGON } }
        });
        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });

        await tick();
        mockClearPlotSelectionCount.mockClear();
        await openAxesEditor(user);

        expect(mockUpdatePlotSelection).not.toHaveBeenCalled();
        expect(mockClearPlotSelectionCount).not.toHaveBeenCalled();
        expect(screen.getByRole('button', { name: 'Apply axes' })).toBeInTheDocument();
        await user.keyboard('{Escape}');
        expect(mockUpdatePlotSelection).not.toHaveBeenCalled();
        expect(screen.queryByRole('button', { name: 'Apply axes' })).not.toBeInTheDocument();
    });

    it('retains the editor and descriptions after failure so the user can retry', async () => {
        const user = userEvent.setup();
        mockEmbedTextAxes.mockRejectedValueOnce(new Error('Service unavailable'));
        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });
        await commitTextAxes(user);
        expect(screen.getByRole('alert')).toHaveTextContent('Could not apply axes');
        expect(screen.getByLabelText('Left')).toHaveValue('young');
        expect(screen.queryByRole('button', { name: 'Reset axes' })).not.toBeInTheDocument();
        mockEmbedTextAxes.mockResolvedValueOnce(TEXT_LAYOUT_AXES);
        await user.click(screen.getByRole('button', { name: 'Apply axes' }));
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();

        // Applying the same texts again does not embed them again.
        await user.click(screen.getByRole('button', { name: 'Edit axes' }));
        await user.click(screen.getByRole('button', { name: 'Apply axes' }));
        expect(mockEmbedTextAxes).toHaveBeenCalledTimes(2);
    });

    it('restores the default layout and keeps descriptions', async () => {
        const user = userEvent.setup();
        vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(
            () => new DOMRect(0, 0, 400, 400)
        );
        const point = new Float32Array([0]);
        plotDataStore.set({ x: point, y: point, category: new Uint8Array([0]) });
        mockEmbedTextAxes.mockResolvedValue(TEXT_LAYOUT_AXES);
        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });
        await commitTextAxes(user);
        await user.click(screen.getByRole('button', { name: 'Pan plot' }));
        rangeSelectionStore.set(SQUARE_POLYGON);
        selectedSampleIdsStore.set(['sample-1']);
        expect(screen.getByText('young')).toBeInTheDocument();
        await user.click(screen.getByRole('button', { name: 'Edit axes' }));
        await user.clear(screen.getByLabelText('Left'));
        await user.type(screen.getByLabelText('Left'), 'night');
        expect(screen.getByText('young')).toBeInTheDocument();
        await user.click(screen.getByRole('button', { name: 'Cancel' }));
        expect(mockEmbedTextAxes).toHaveBeenCalledTimes(1);
        await user.click(screen.getByRole('button', { name: 'Reset axes' }));
        expect(screen.queryByRole('button', { name: 'Apply axes' })).not.toBeInTheDocument();
        expect(screen.getByTestId('plot-viewport')).toHaveTextContent('null');
        expect(mockClearPlotSelectionCount).toHaveBeenCalled();
        expect(screen.queryByText('young')).not.toBeInTheDocument();
        // Back on PaCMAP, the button reads "Define axes" again.
        await user.click(screen.getByRole('button', { name: 'Define axes' }));
        expect(screen.getByLabelText('Left')).toHaveValue('night');
        expect(screen.getByLabelText('Right')).toHaveValue('old');
        expect(screen.getByLabelText('Bottom')).toHaveValue('sad');
        expect(screen.getByLabelText('Top')).toHaveValue('happy');
        await user.click(screen.getByRole('button', { name: 'Apply axes' }));
        expect(screen.getByText('night')).toBeInTheDocument();
        expect(screen.getByTestId('plot-viewport')).toHaveTextContent(
            JSON.stringify({ x: 0, y: 0, scale: 5 })
        );
    });

    it('disables reset while applying edited axes', async () => {
        const user = userEvent.setup();
        vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(
            () => new DOMRect(0, 0, 400, 400)
        );
        const point = new Float32Array([0]);
        plotDataStore.set({ x: point, y: point, category: new Uint8Array([0]) });
        mockEmbedTextAxes.mockResolvedValueOnce(TEXT_LAYOUT_AXES);
        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });
        await commitTextAxes(user);
        await user.click(screen.getByRole('button', { name: 'Edit axes' }));
        await user.type(screen.getByLabelText('Left'), ' person');
        let finish!: (axes: typeof TEXT_LAYOUT_AXES) => void;
        mockEmbedTextAxes.mockReturnValueOnce(
            new Promise((resolve) => {
                finish = resolve;
            })
        );
        await user.click(screen.getByRole('button', { name: 'Apply axes' }));
        const resetButton = screen.getByRole('button', { name: 'Reset axes' });
        expect(resetButton).toBeDisabled();
        await user.click(resetButton);
        // Escape does not close the popover while the axes are applied.
        await user.keyboard('{Escape}');
        expect(screen.getByRole('button', { name: 'Applying…' })).toBeInTheDocument();
        expect(screen.getByText('young')).toBeInTheDocument();
        finish(TEXT_LAYOUT_AXES);
        await waitFor(() =>
            expect(screen.queryByRole('button', { name: 'Applying…' })).not.toBeInTheDocument()
        );
    });

    it('hides the axis descriptions while the plot is not rendered', async () => {
        const user = userEvent.setup();
        mockEmbedTextAxes.mockResolvedValueOnce(TEXT_LAYOUT_AXES);
        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });
        await commitTextAxes(user);
        expect(await screen.findByRole('button', { name: 'Edit axes' })).toBeInTheDocument();
        expect(screen.queryByText('young')).not.toBeInTheDocument();
    });

    it('unmounts the plot and shows the loader while a new color-by loads', async () => {
        const user = userEvent.setup();
        vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(
            () => new DOMRect(0, 0, 400, 400)
        );
        const point = new Float32Array([0]);
        plotDataStore.set({ x: point, y: point, category: new Uint8Array([0]) });
        const loaded = { data: { columns: {}, legend: new Map() } };
        // Only the query of the new color-by is still loading. The plot creates its query once,
        // so the result follows the current request.
        vi.mocked(useEmbeddings).mockImplementation((getParams) => {
            const result = (): Record<string, unknown> =>
                getParams().colorBy ? { isLoading: true } : loaded;
            return new Proxy({}, { get: (_, key: string) => result()[key] }) as never;
        });
        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });
        expect(await screen.findByTestId('plot-viewport')).toBeInTheDocument();

        await user.click(screen.getByTestId('plot-color-by-button'));
        await user.click(await screen.findByRole('option', { name: 'tags' }));

        expect(screen.getByText('Loading embeddings data...')).toBeInTheDocument();
        expect(screen.queryByTestId('plot-viewport')).not.toBeInTheDocument();
    });

    it('keeps hidden classes when the legend changes', async () => {
        const embeddingsResult = mockEmbeddingsQuery({ data: { columns: {}, legend: new Map() } });
        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });
        await tick();

        embeddingsResult.set({ data: { columns: {}, legend: new Map([[3, 'dog']]) } });
        await tick();

        expect(mockClearForColorByMode).not.toHaveBeenCalled();
    });

    it('clears hidden classes when the color-by mode changes', async () => {
        const user = userEvent.setup();
        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });
        await tick();

        await user.click(screen.getByTestId('plot-color-by-button'));
        await user.click(await screen.findByRole('option', { name: 'metadata.split' }));
        await tick();

        expect(mockClearForColorByMode).toHaveBeenCalledOnce();
    });

    it('creating a tag keeps hidden classes', async () => {
        const user = userEvent.setup();
        render(PlotPanel, { props: { collectionId: 'test-collection-id' } });
        await user.click(screen.getByTestId('plot-color-by-button'));
        await user.click(await screen.findByRole('option', { name: 'tags' }));
        await tick();
        mockClearForColorByMode.mockClear();

        tagsStore.update((tags) => [...tags, { tag_id: 'tag-c', name: 'gamma' }]);
        await tick();

        expect(lastEmbeddingsParams().colorBy).toMatchObject({
            tag_ids: ['tag-a', 'tag-b', 'tag-c']
        });
        expect(mockClearForColorByMode).not.toHaveBeenCalled();
    });
    describe('while embeddings load', () => {
        it('keeps the plot on screen while a filter change loads', async () => {
            vi.mocked(useEmbeddings).mockReturnValue({
                isError: false,
                error: null,
                isLoading: false,
                isPlaceholderData: true,
                data: { columns: {}, legend: new Map() }
            } as unknown as ReturnType<typeof useEmbeddings>);

            render(PlotPanel, { props: { collectionId: 'test-collection-id' } });

            expect(screen.queryByText('Loading embeddings data...')).not.toBeInTheDocument();
            expect(screen.getByTestId('plot-loading-indicator')).toBeInTheDocument();
        });

        it('ignores a lasso and a pick on the old points', async () => {
            vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(
                () => new DOMRect(0, 0, 400, 400)
            );
            const point = new Float32Array([0]);
            plotDataStore.set({ x: point, y: point, category: new Uint8Array([0]) });
            vi.mocked(useEmbeddings).mockReturnValue({
                isLoading: false,
                isPlaceholderData: true,
                data: { columns: {}, legend: new Map() }
            } as unknown as ReturnType<typeof useEmbeddings>);
            render(PlotPanel, { props: { collectionId: 'test-collection-id' } });
            const plot = await screen.findByTestId('plot-viewport');

            rangeSelectionStore.set(SQUARE_POLYGON);
            selectedSampleIdsStore.set(['sample-1']);
            await fireEvent.mouseUp(window);
            plot.dispatchEvent(new MouseEvent('pointerdown', { bubbles: true, shiftKey: true }));
            await fireEvent.click(screen.getByRole('button', { name: 'Pick point' }));

            expect(mockSetRangeSelectionForCollection).toHaveBeenCalledWith(
                'test-collection-id',
                null
            );
            expect(mockUpdatePlotSelection).not.toHaveBeenCalled();
            expect(mockSetPlotSelectionCount).not.toHaveBeenCalled();
        });

        it('ignores a lasso and a pick that start on the old points and end on the new ones', async () => {
            vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(
                () => new DOMRect(0, 0, 400, 400)
            );
            const point = new Float32Array([0]);
            plotDataStore.set({ x: point, y: point, category: new Uint8Array([0]) });
            const embeddings = {
                isLoading: false,
                isPlaceholderData: true,
                data: { columns: {}, legend: new Map() }
            };
            vi.mocked(useEmbeddings).mockReturnValue(
                embeddings as unknown as ReturnType<typeof useEmbeddings>
            );
            render(PlotPanel, { props: { collectionId: 'test-collection-id' } });
            const plot = await screen.findByTestId('plot-viewport');

            plot.dispatchEvent(new MouseEvent('pointerdown', { bubbles: true, shiftKey: true }));
            embeddings.isPlaceholderData = false;
            rangeSelectionStore.set(SQUARE_POLYGON);
            selectedSampleIdsStore.set(['sample-1']);
            await fireEvent.mouseUp(window);
            await fireEvent.click(screen.getByRole('button', { name: 'Pick point' }));

            expect(mockUpdatePlotSelection).not.toHaveBeenCalled();
            expect(mockSetPlotSelectionCount).not.toHaveBeenCalled();
        });

        it('shows the full loader when the color-by changes', async () => {
            vi.mocked(useEmbeddings).mockReturnValue({
                isError: false,
                error: null,
                isLoading: true,
                isPlaceholderData: false,
                data: undefined
            } as unknown as ReturnType<typeof useEmbeddings>);

            render(PlotPanel, { props: { collectionId: 'test-collection-id' } });

            expect(screen.getByText('Loading embeddings data...')).toBeInTheDocument();
            expect(screen.queryByTestId('plot-loading-indicator')).not.toBeInTheDocument();
        });

        it('creates the embeddings query once', async () => {
            render(PlotPanel, { props: { collectionId: 'test-collection-id' } });

            imageFilterStore.set({ sample_filter: { tag_ids: ['tag-a'] } });
            await tick();
            imageFilterStore.set({ sample_filter: { tag_ids: ['tag-b'] } });
            await tick();

            expect(useEmbeddings).toHaveBeenCalledTimes(1);
            expect(lastEmbeddingsParams().filters).toEqual({
                sample_filter: { tag_ids: ['tag-b'] }
            });
        });
    });
    describe('with Excluded hidden', () => {
        const lastPlotHiddenCategories = () =>
            (usePlotDataSpy.mock.lastCall![0] as { hiddenCategories: Set<number> })
                .hiddenCategories;

        beforeEach(() => {
            hiddenCategoriesStore.set(new Set([EXCLUDED_BY_FILTERS_CATEGORY]));
        });

        it('keeps Excluded hidden after the selection is committed', async () => {
            imageFilterStore.set({
                sample_filter: { embedding_region: { polygon: SQUARE_POLYGON } }
            });
            render(PlotPanel, { props: { collectionId: 'test-collection-id' } });
            await tick();

            expect(lastPlotHiddenCategories().has(EXCLUDED_BY_FILTERS_CATEGORY)).toBe(true);
        });

        it('shows Excluded while the user draws, so the canvas does not go blank', async () => {
            render(PlotPanel, { props: { collectionId: 'test-collection-id' } });

            rangeSelectionStore.set(SQUARE_POLYGON);
            await tick();

            expect(lastPlotHiddenCategories().has(EXCLUDED_BY_FILTERS_CATEGORY)).toBe(false);
        });

        it('shows Excluded while points are picked, so the other points stay pickable', async () => {
            imageFilterStore.set({ sample_filter: { sample_ids: ['sample-1'] } });
            render(PlotPanel, { props: { collectionId: 'test-collection-id' } });
            await tick();

            expect(lastPlotHiddenCategories().has(EXCLUDED_BY_FILTERS_CATEGORY)).toBe(false);
        });
    });
});
