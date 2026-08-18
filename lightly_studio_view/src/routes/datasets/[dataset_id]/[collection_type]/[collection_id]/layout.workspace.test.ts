import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import * as appState from '$app/state';
import { tick } from 'svelte';
import '@testing-library/jest-dom';

import { APP_ROUTES } from '$lib/routes';
import type { PanelType } from '$lib/hooks/useGlobalStorage';
import { SampleType } from '$lib/api/lightly_studio_local';
import type { LayoutLoadResult } from './+layout';
import LayoutWorkspaceTestWrapper from './LayoutWorkspaceTestWrapper.test.svelte';

vi.mock('$app/environment', () => ({ browser: false }));
vi.mock('$app/navigation', () => ({ afterNavigate: vi.fn() }));

vi.mock('$lib/api/lightly_studio_local/sdk.gen', () => ({
    readAnnotationEmbedding: vi.fn()
}));
vi.mock('$lib/workers/maskRendererPool', () => ({
    shutdownMaskRendererPool: vi.fn()
}));
vi.mock('$lib/hooks/useEmbeddingFilter/useEmbeddingFilterForAnnotations', () => ({
    clearAnnotationPlotSelection: vi.fn()
}));
vi.mock('$lib/utils/buildImageFilter', () => ({
    buildImageFilter: vi.fn(() => ({}))
}));
vi.mock('$lib/utils/buildAnnotationCountsFilters', () => ({
    buildVideoAnnotationCountsFilter: vi.fn(() => ({})),
    buildVideoFrameAnnotationCountsFilter: vi.fn(() => ({}))
}));
vi.mock('$lib/components/GridItem', () => ({
    GRID_IMAGE_SEARCH_DROP_EVENT: 'grid-image-search-drop'
}));

vi.mock('paneforge', async () => {
    const { default: Stub } = await import('./LayoutStub.test.svelte');
    return { PaneGroup: Stub, Pane: Stub, PaneResizer: Stub };
});
vi.mock('$lib/components', async () => {
    const { default: Stub } = await import('./LayoutStub.test.svelte');
    return {
        Button: Stub,
        CombinedMetadataDimensionsFilters: Stub,
        DatasetGridHeader: Stub,
        Footer: Stub,
        LabelsMenu: Stub,
        MetadataFilterChips: Stub,
        SelectionPill: Stub,
        ShowFiltersButton: Stub,
        TagsMenu: Stub,
        SidePanelTabs: Stub,
        Header: Stub,
        Separator: Stub
    };
});
vi.mock('$lib/components/ui/tooltip', async () => {
    const { default: Stub } = await import('./LayoutStub.test.svelte');
    return { Tooltip: Stub };
});
vi.mock('$lib/components/ui/separator/separator.svelte', async () => ({
    default: (await import('./LayoutStub.test.svelte')).default
}));
vi.mock('$lib/components/QueryEditorPanel/QueryEditorPanel.svelte', async () => ({
    default: (await import('./LayoutStub.test.svelte')).default
}));
vi.mock('$lib/components/Header/MenuDialogHost.svelte', async () => ({
    default: (await import('./LayoutStub.test.svelte')).default
}));
vi.mock('$lib/components/QueryControl/QueryControl.svelte', async () => ({
    default: (await import('./LayoutStub.test.svelte')).default
}));
vi.mock('$lib/components/AnnotationCollectionsMenu/AnnotationCollectionsMenu.svelte', async () => ({
    default: (await import('./LayoutStub.test.svelte')).default
}));
vi.mock(
    '$lib/components/EmbeddingSelectionFilterItem/EmbeddingSelectionFilterItem.svelte',
    async () => ({ default: (await import('./LayoutStub.test.svelte')).default })
);
vi.mock('$lib/components/ConfusionCellFilterItem', async () => ({
    default: (await import('./LayoutStub.test.svelte')).default
}));

vi.mock('$lib/hooks/useGlobalStorage');
vi.mock('$lib/hooks/useHideAnnotations', () => ({
    useHideAnnotations: vi.fn(() => ({ handleKeyEvent: vi.fn() }))
}));
vi.mock('$lib/hooks/useHasEmbeddings/useHasEmbeddings', () => ({
    useHasEmbeddings: vi.fn(() => ({ data: undefined }))
}));
vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: vi.fn(() => ({ data: undefined }))
}));
vi.mock('$lib/hooks/useAnnotationsFilter/useAnnotationsFilter', () => ({
    useAnnotationsFilter: vi.fn(() => ({
        annotationFilter: writable(null),
        annotationFilterRows: [],
        toggleAnnotationFilterSelection: vi.fn(),
        setAnnotationCounts: vi.fn(),
        pruneInvalidSelections: vi.fn()
    }))
}));
vi.mock('$lib/hooks/useDimensions/useDimensions', () => ({
    useDimensions: vi.fn(() => ({ dimensionsValues: writable({}) }))
}));
vi.mock('$lib/hooks/useVideoAnnotationsCount/useVideoAnnotationsCount.js', () => ({
    useVideoAnnotationCounts: vi.fn(() => ({ data: undefined }))
}));
vi.mock('$lib/hooks/useMetadataFilters/useMetadataFilters.js', () => ({
    useMetadataFilters: vi.fn(() => ({
        metadataValues: writable({}),
        metadataBounds: writable({}),
        updateMetadataValues: vi.fn()
    })),
    createMetadataFilters: vi.fn(() => undefined)
}));
vi.mock('$lib/hooks/useVideoFrameAnnotationsCount/useVideoFrameAnnotationsCount.js', () => ({
    useVideoFrameAnnotationCounts: vi.fn(() => ({ data: undefined }))
}));
vi.mock('$lib/hooks/useVideoFramesBounds/useVideoFramesBounds.js', () => ({
    useVideoFramesBounds: vi.fn(() => ({ videoFramesBoundsValues: writable({}) }))
}));
vi.mock('$lib/hooks/useVideosBounds/useVideosBounds.js', () => ({
    useVideoBounds: vi.fn(() => ({ videoBoundsValues: writable({}) }))
}));
vi.mock('$lib/hooks/useImageFilters/useImageFilters', () => ({
    useImageFilters: vi.fn(() => ({ imageFilter: writable(null) }))
}));
vi.mock('$lib/hooks/useVideoFilters/useVideoFilters', () => ({
    useVideoFilters: vi.fn(() => ({ videoFilter: writable(null) }))
}));
vi.mock('$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter', () => ({
    useAnnotationCollectionsFilter: vi.fn(() => ({
        selectedCollectionIds: writable([]),
        allSourcesHidden: writable(false)
    }))
}));
vi.mock('$lib/hooks/useSeedAnnotationSourceFilter/useSeedAnnotationSourceFilter.svelte', () => ({
    useSeedAnnotationSourceFilter: vi.fn()
}));
vi.mock('$lib/hooks', () => ({
    useSelectionSummary: vi.fn(() => ({
        selectedCount: writable(0),
        clearSelection: vi.fn()
    })),
    useImageAnnotationCounts: vi.fn(() => ({ data: undefined })),
    useImageAnnotationCountsQueryKey: ['imageAnnotationCounts'],
    useNumericMetadataDistribution: vi.fn(() => ({ data: undefined })),
    useCategoricalMetadataDistribution: vi.fn(() => ({
        data: undefined,
        isFetching: false,
        error: null,
        refetch: vi.fn()
    })),
    usePostHog: vi.fn(() => ({ trackEvent: vi.fn() })),
    useTrackSampleInspected: vi.fn()
}));
vi.mock('$lib/hooks/useSelectAll/useSelectAll', () => ({
    useSelectAll: vi.fn(() => ({ handleSelectAll: vi.fn() }))
}));
vi.mock('$lib/hooks/useSearchEmbedding/useSearchEmbedding', () => ({
    useSearchEmbedding: vi.fn(() => ({
        image: writable(null),
        isPending: writable(false),
        setText: vi.fn(),
        setImage: vi.fn(),
        setEmbedding: vi.fn(),
        clear: vi.fn(),
        onError: vi.fn()
    }))
}));
vi.mock('$lib/hooks/useEvaluationRuns/useEvaluationRuns', () => ({
    useEvaluationRuns: vi.fn(() => ({ data: undefined, isLoading: false, error: null }))
}));

import * as useGlobalStorageModule from '$lib/hooks/useGlobalStorage';
import * as useHasEmbeddingsModule from '$lib/hooks/useHasEmbeddings/useHasEmbeddings';

let mockActivePanel: ReturnType<typeof writable<PanelType>>;
let mockFilterPanelCollapsed: ReturnType<typeof writable<boolean>>;

function setPageRoute(routeId: string | null): void {
    vi.spyOn(appState, 'page', 'get').mockReturnValue({
        route: { id: routeId },
        params: {
            dataset_id: 'test-dataset-id',
            collection_id: 'test-collection-id',
            collection_type: 'image'
        }
    } as unknown as typeof appState.page);
}

beforeEach(() => {
    vi.clearAllMocks();

    mockActivePanel = writable<PanelType>('none');
    mockFilterPanelCollapsed = writable(false);

    vi.mocked(useGlobalStorageModule.useGlobalStorage).mockReturnValue({
        activePanel: mockActivePanel,
        setActivePanel: vi.fn(),
        filterPanelCollapsed: mockFilterPanelCollapsed,
        toggleFilterPanelCollapsed: vi.fn(),
        filteredSampleCount: writable(0),
        filteredAnnotationCount: writable(0),
        textEmbedding: writable(undefined),
        collections: writable({}),
        retrieveParentCollection: vi.fn(() => null)
    } as Partial<ReturnType<typeof useGlobalStorageModule.useGlobalStorage>> as ReturnType<
        typeof useGlobalStorageModule.useGlobalStorage
    >);

    vi.mocked(useHasEmbeddingsModule.useHasEmbeddings).mockReturnValue({
        data: undefined
    } as Partial<ReturnType<typeof useHasEmbeddingsModule.useHasEmbeddings>> as ReturnType<
        typeof useHasEmbeddingsModule.useHasEmbeddings
    >);
});

const defaultProps = {
    data: {
        collection: {
            collection_id: 'test-collection-id',
            dataset_id: 'test-dataset-id',
            name: 'Test Collection',
            sample_type: SampleType.IMAGE,
            total_sample_count: 10
        } as Partial<LayoutLoadResult['collection']> as LayoutLoadResult['collection'],
        collectionHierarchy: [],
        globalStorage: {
            setLastGridType: vi.fn(),
            clearSelectedSamples: vi.fn(),
            clearSelectedSampleAnnotationCrops: vi.fn()
        } as Partial<LayoutLoadResult['globalStorage']> as LayoutLoadResult['globalStorage'],
        sampleSize: writable({ width: 6, height: 6 })
    }
};

// Collection-grid workspace rendering

describe('+layout.svelte collection-grid workspace', () => {
    it('renders filter panel on images route', async () => {
        setPageRoute(APP_ROUTES.images);
        render(LayoutWorkspaceTestWrapper, { props: defaultProps });
        await tick();

        expect(screen.getByTestId('filter-panel-body')).toBeInTheDocument();
    });

    it('renders filter panel on annotations route', async () => {
        setPageRoute(APP_ROUTES.annotations);
        render(LayoutWorkspaceTestWrapper, { props: defaultProps });
        await tick();

        expect(screen.getByTestId('filter-panel-body')).toBeInTheDocument();
    });

    it('renders filter panel on videos route', async () => {
        setPageRoute(APP_ROUTES.videos);
        render(LayoutWorkspaceTestWrapper, { props: defaultProps });
        await tick();

        expect(screen.getByTestId('filter-panel-body')).toBeInTheDocument();
    });

    it('renders filter panel on frames route', async () => {
        setPageRoute(APP_ROUTES.frames);
        render(LayoutWorkspaceTestWrapper, { props: defaultProps });
        await tick();

        expect(screen.getByTestId('filter-panel-body')).toBeInTheDocument();
    });

    it('renders filter panel on groups route', async () => {
        setPageRoute(APP_ROUTES.groups);
        render(LayoutWorkspaceTestWrapper, { props: defaultProps });
        await tick();

        expect(screen.getByTestId('filter-panel-body')).toBeInTheDocument();
    });

    it('renders child route content on images route', async () => {
        setPageRoute(APP_ROUTES.images);
        render(LayoutWorkspaceTestWrapper, { props: defaultProps });
        await tick();

        expect(screen.getByTestId('layout-test-child')).toBeInTheDocument();
    });
});

// Details routes bypass the workspace

describe('+layout.svelte details-route bypass', () => {
    it('does NOT render filter panel on image-details route', async () => {
        setPageRoute(APP_ROUTES.imageDetails);
        render(LayoutWorkspaceTestWrapper, { props: defaultProps });
        await tick();

        expect(screen.queryByTestId('filter-panel-body')).not.toBeInTheDocument();
    });

    it('still renders child content on image-details route', async () => {
        setPageRoute(APP_ROUTES.imageDetails);
        render(LayoutWorkspaceTestWrapper, { props: defaultProps });
        await tick();

        expect(screen.getByTestId('layout-test-child')).toBeInTheDocument();
    });

    it('does NOT render filter panel on annotation-details route', async () => {
        setPageRoute(APP_ROUTES.annotationDetails);
        render(LayoutWorkspaceTestWrapper, { props: defaultProps });
        await tick();

        expect(screen.queryByTestId('filter-panel-body')).not.toBeInTheDocument();
    });

    it('still renders child content on annotation-details route', async () => {
        setPageRoute(APP_ROUTES.annotationDetails);
        render(LayoutWorkspaceTestWrapper, { props: defaultProps });
        await tick();

        expect(screen.getByTestId('layout-test-child')).toBeInTheDocument();
    });

    it('does NOT render filter panel on video-details route', async () => {
        setPageRoute(APP_ROUTES.videoDetails);
        render(LayoutWorkspaceTestWrapper, { props: defaultProps });
        await tick();

        expect(screen.queryByTestId('filter-panel-body')).not.toBeInTheDocument();
    });

    it('still renders child content on video-details route', async () => {
        setPageRoute(APP_ROUTES.videoDetails);
        render(LayoutWorkspaceTestWrapper, { props: defaultProps });
        await tick();

        expect(screen.getByTestId('layout-test-child')).toBeInTheDocument();
    });

    it('does NOT render workspace frame on frame-details route', async () => {
        setPageRoute(APP_ROUTES.framesDetails);
        render(LayoutWorkspaceTestWrapper, { props: defaultProps });
        await tick();

        expect(screen.queryByTestId('workspace-body')).not.toBeInTheDocument();
    });

    it('still renders child content on frame-details route', async () => {
        setPageRoute(APP_ROUTES.framesDetails);
        render(LayoutWorkspaceTestWrapper, { props: defaultProps });
        await tick();

        expect(screen.getByTestId('layout-test-child')).toBeInTheDocument();
    });
});

// Filter sidebar collapse/expand

describe('filter sidebar collapse/expand', () => {
    it('filter panel is visible (not collapsed) by default', async () => {
        setPageRoute(APP_ROUTES.images);
        mockFilterPanelCollapsed.set(false);

        render(LayoutWorkspaceTestWrapper, { props: defaultProps });
        await tick();

        expect(screen.getByTestId('filter-panel-body')).toHaveAttribute('aria-hidden', 'false');
    });

    it('filter panel is collapsed when filterPanelCollapsed is true', async () => {
        setPageRoute(APP_ROUTES.images);
        mockFilterPanelCollapsed.set(true);

        render(LayoutWorkspaceTestWrapper, { props: defaultProps });
        await tick();

        expect(screen.getByTestId('filter-panel-body')).toHaveAttribute('aria-hidden', 'true');
    });

    it('filter panel stays in DOM when collapsed (mount-time effects must still run)', async () => {
        setPageRoute(APP_ROUTES.images);
        mockFilterPanelCollapsed.set(true);

        render(LayoutWorkspaceTestWrapper, { props: defaultProps });
        await tick();

        expect(screen.getByTestId('filter-panel-body')).toBeInTheDocument();
    });

    it('filter panel is not rendered on a details route regardless of collapse state', async () => {
        setPageRoute(APP_ROUTES.imageDetails);
        mockFilterPanelCollapsed.set(false);

        render(LayoutWorkspaceTestWrapper, { props: defaultProps });
        await tick();

        expect(screen.queryByTestId('filter-panel-body')).not.toBeInTheDocument();
    });
});

// Right panel – main content stability

describe('right panel – main content stability', () => {
    it('renders child content when no right panel is open', async () => {
        setPageRoute(APP_ROUTES.images);
        mockActivePanel.set('none');

        render(LayoutWorkspaceTestWrapper, { props: defaultProps });
        await tick();

        expect(screen.getByTestId('layout-test-child')).toBeInTheDocument();
        expect(screen.queryByTestId('pane-group-layout')).not.toBeInTheDocument();
    });

    it('child content is still present after opening an evaluationRuns panel', async () => {
        setPageRoute(APP_ROUTES.images);
        mockActivePanel.set('none');

        render(LayoutWorkspaceTestWrapper, { props: defaultProps });
        await tick();

        mockActivePanel.set('evaluationRuns');
        await tick();

        expect(screen.getByTestId('layout-test-child')).toBeInTheDocument();
        expect(screen.getByTestId('pane-group-layout')).toBeInTheDocument();
    });

    it('child content is still present after closing the panel', async () => {
        setPageRoute(APP_ROUTES.images);
        mockActivePanel.set('evaluationRuns');

        render(LayoutWorkspaceTestWrapper, { props: defaultProps });
        await tick();

        mockActivePanel.set('none');
        await tick();

        expect(screen.getByTestId('layout-test-child')).toBeInTheDocument();
        expect(screen.queryByTestId('pane-group-layout')).not.toBeInTheDocument();
    });

    it('evaluationRuns panel is not shown on videos route even when requested', async () => {
        setPageRoute(APP_ROUTES.videos);
        mockActivePanel.set('evaluationRuns');

        render(LayoutWorkspaceTestWrapper, { props: defaultProps });
        await tick();

        expect(screen.queryByTestId('pane-group-layout')).not.toBeInTheDocument();
    });

    it('queryEditor panel is not shown on videos route even when requested', async () => {
        setPageRoute(APP_ROUTES.videos);
        mockActivePanel.set('queryEditor');

        render(LayoutWorkspaceTestWrapper, { props: defaultProps });
        await tick();

        expect(screen.queryByTestId('pane-group-layout')).not.toBeInTheDocument();
    });
});

// SidePanelTabs availability

describe('SidePanelTabs availability', () => {
    it('is present on images route', async () => {
        setPageRoute(APP_ROUTES.images);

        render(LayoutWorkspaceTestWrapper, { props: defaultProps });
        await tick();

        expect(screen.getByTestId('side-panel-tabs')).toBeInTheDocument();
    });

    it('is absent on a details route', async () => {
        setPageRoute(APP_ROUTES.imageDetails);

        render(LayoutWorkspaceTestWrapper, { props: defaultProps });
        await tick();

        expect(screen.queryByTestId('side-panel-tabs')).not.toBeInTheDocument();
    });

    it('is absent on a collection-grid route without embeddings', async () => {
        setPageRoute(APP_ROUTES.annotations);

        render(LayoutWorkspaceTestWrapper, { props: defaultProps });
        await tick();

        expect(screen.queryByTestId('side-panel-tabs')).not.toBeInTheDocument();
    });

    it('is present on annotations route when embeddings exist', async () => {
        setPageRoute(APP_ROUTES.annotations);
        vi.mocked(useHasEmbeddingsModule.useHasEmbeddings).mockReturnValue({
            data: true
        } as Partial<ReturnType<typeof useHasEmbeddingsModule.useHasEmbeddings>> as ReturnType<
            typeof useHasEmbeddingsModule.useHasEmbeddings
        >);

        render(LayoutWorkspaceTestWrapper, { props: defaultProps });
        await tick();

        expect(screen.getByTestId('side-panel-tabs')).toBeInTheDocument();
    });
});
