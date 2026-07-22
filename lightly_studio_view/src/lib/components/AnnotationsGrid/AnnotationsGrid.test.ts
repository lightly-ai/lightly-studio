import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import '@testing-library/jest-dom';
import { type Writable } from 'svelte/store';
import {
    AnnotationType,
    SampleType,
    type AnnotationView,
    type AnnotationWithPayloadView,
    type ImageAnnotationView
} from '$lib/api/lightly_studio_local';
import AnnotationsGrid from './AnnotationsGrid.svelte';

const mocks = vi.hoisted(() => ({
    annotationsData: [] as AnnotationWithPayloadView[],
    updateAnnotations: vi.fn(),
    updateAnnotationsRaw: vi.fn(),
    refresh: vi.fn(),
    isPendingStore: null as unknown as Writable<boolean>,
    pickedAnnotationIds: null as unknown as Writable<Record<string, Set<string>>>,
    toggleSampleAnnotationCropSelection: vi.fn(),
    clearSelectedSampleAnnotationCrops: vi.fn(),
    getCollectionVersion: vi.fn(),
    setfilteredAnnotationCount: vi.fn(),
    addReversibleAction: vi.fn(),
    clearReversibleActions: vi.fn(),
    textEmbeddingStore: null as unknown as Writable<undefined>,
    isEditingModeStore: null as unknown as Writable<boolean>
}));

vi.mock('$app/navigation', () => ({
    goto: vi.fn(),
    afterNavigate: vi.fn()
}));

vi.mock('$app/state', async () => {
    const { writable } = await import('svelte/store');
    mocks.isEditingModeStore = writable(false);
    return {
        page: {
            params: { dataset_id: 'ds-1', collection_type: 'object-detection' },
            data: { globalStorage: { isEditingMode: mocks.isEditingModeStore } }
        }
    };
});

vi.mock('$lib/hooks/useAnnotationsFilter/useAnnotationsFilter', async () => {
    const { writable } = await import('svelte/store');
    return {
        useSelectedAnnotationsFilter: vi.fn(() => ({
            selectedAnnotationFilterIdsArray: writable<string[]>([])
        }))
    };
});

vi.mock('$lib/hooks/useTags/useTags', async () => {
    const { writable } = await import('svelte/store');
    return {
        useTags: vi.fn(() => ({
            tagsSelected: writable(new Set<string>())
        }))
    };
});

vi.mock('$lib/hooks/useSettings', async () => {
    const { writable } = await import('svelte/store');
    return {
        useSettings: vi.fn(() => ({
            showAnnotationTextLabelsStore: writable(true),
            gridViewThumbnailQualityStore: writable(75)
        }))
    };
});

vi.mock('$lib/hooks/useGlobalStorage', async () => {
    const { writable } = await import('svelte/store');
    mocks.isPendingStore = writable(false);
    mocks.pickedAnnotationIds = writable({});
    mocks.textEmbeddingStore = writable(undefined);
    return {
        useGlobalStorage: vi.fn(() => ({
            getCollectionVersion: mocks.getCollectionVersion,
            setfilteredAnnotationCount: mocks.setfilteredAnnotationCount,
            addReversibleAction: mocks.addReversibleAction,
            clearReversibleActions: mocks.clearReversibleActions,
            textEmbedding: mocks.textEmbeddingStore,
            selectedSampleAnnotationCropIds: mocks.pickedAnnotationIds,
            toggleSampleAnnotationCropSelection: mocks.toggleSampleAnnotationCropSelection,
            clearSelectedSampleAnnotationCrops: mocks.clearSelectedSampleAnnotationCrops
        }))
    };
});

vi.mock('$lib/hooks/useEmbeddingFilter/useEmbeddingFilterForAnnotations', async () => {
    const { writable } = await import('svelte/store');
    return {
        useAnnotationPlotSelection: vi.fn(() => ({
            annotationPlotRegion: writable(null)
        }))
    };
});

vi.mock('$lib/hooks/useHasEmbeddings/useHasEmbeddings', () => ({
    useHasEmbeddings: vi.fn(() => ({ data: null }))
}));

vi.mock('$lib/hooks/useAnnotationsInfinite/useAnnotationsInfinite', () => ({
    useAnnotationsInfinite: vi.fn(() => ({
        annotations: {
            data: {
                pages: [{ data: mocks.annotationsData, total_count: mocks.annotationsData.length }]
            },
            isSuccess: true,
            isFetched: true,
            isPending: false,
            isError: false,
            hasNextPage: false,
            isFetchingNextPage: false,
            fetchNextPage: vi.fn()
        },
        updateAnnotations: mocks.updateAnnotations,
        refresh: mocks.refresh,
        isPending: mocks.isPendingStore
    }))
}));

vi.mock('$lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation', () => ({
    useUpdateAnnotationsMutation: vi.fn(() => ({
        updateAnnotations: mocks.updateAnnotationsRaw
    }))
}));

vi.mock('$lib/hooks/useScrollRestoration/useScrollRestoration', () => ({
    useScrollRestoration: vi.fn(() => ({
        initialize: vi.fn(),
        savePosition: vi.fn(),
        getRestoredPosition: vi.fn().mockReturnValue(0)
    }))
}));

vi.mock('$lib/hooks/useAuth/useAuth', () => ({
    default: vi.fn(() => ({ user: { role: 'admin' } }))
}));

vi.mock('$lib/hooks/useAuth/hasMinimumRole', () => ({
    hasMinimumRole: vi.fn(() => true)
}));

vi.mock('$lib/components/GridContainer', async () => {
    const { default: MockGridContainer } =
        await import('../GridContainer/GridContainer.mock.svelte');
    return { GridContainer: MockGridContainer };
});

vi.mock('$lib/components/Grid', async () => {
    const { default: MockGrid } = await import('../Grid/Grid.mock.svelte');
    return { Grid: MockGrid };
});

vi.mock('$lib/components/GridItem', async () => {
    const { default: MockGridItem } = await import('../GridItem/GridItem.mock.svelte');
    return { GridItem: MockGridItem };
});

vi.mock('$lib/components', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/components')>();
    const { default: MockAnnotationsGridItem } =
        await import('./AnnotationsGridItem/AnnotationsGridItem.mock.svelte');
    const { default: MockSelectableBox } =
        await import('../SelectableBox/SelectableBox.mock.svelte');
    return {
        ...actual,
        AnnotationsGridItem: MockAnnotationsGridItem,
        SelectableBox: MockSelectableBox
    };
});

vi.mock('./AnnotationClassificationGridItem/AnnotationClassificationGridItem.svelte', async () => {
    const { default: MockClassification } =
        await import('./AnnotationClassificationGridItem/AnnotationClassificationGridItem.mock.svelte');
    return { default: MockClassification };
});

vi.mock('./SelectedAnnotations/SelectedAnnotations.svelte', async () => {
    const { default: MockSelectedAnnotations } =
        await import('./SelectedAnnotations/SelectedAnnotations.mock.svelte');
    return { default: MockSelectedAnnotations };
});

vi.mock('./AnnotationItem/renderCropObjectUrl', () => ({
    renderCropObjectUrl: vi.fn().mockResolvedValue(null)
}));

function buildClassificationAnnotation(id: string, labelName = 'cat'): AnnotationWithPayloadView {
    return {
        parent_sample_type: SampleType.IMAGE,
        annotation: {
            sample_id: id,
            annotation_type: AnnotationType.CLASSIFICATION,
            annotation_label: { annotation_label_name: labelName },
            annotation_collection_id: 'col-1',
            parent_sample_id: 'img-1'
        } as unknown as AnnotationView,
        parent_sample_data: {
            sample_id: 'img-1',
            width: 800,
            height: 600
        } as unknown as ImageAnnotationView
    };
}

function buildOdAnnotation(id: string): AnnotationWithPayloadView {
    return {
        parent_sample_type: SampleType.IMAGE,
        annotation: {
            sample_id: id,
            annotation_type: AnnotationType.OBJECT_DETECTION,
            annotation_label: { annotation_label_name: 'dog' },
            annotation_collection_id: 'col-1',
            parent_sample_id: 'img-2',
            object_detection_details: { x: 0, y: 0, width: 100, height: 100 }
        } as unknown as AnnotationView,
        parent_sample_data: {
            sample_id: 'img-2',
            width: 640,
            height: 480
        } as unknown as ImageAnnotationView
    };
}

function renderGrid() {
    mocks.getCollectionVersion.mockResolvedValue('v1');
    return render(AnnotationsGrid, { props: { collection_id: 'col-1', itemWidth: 3 } });
}

describe('AnnotationsGrid', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.annotationsData = [];
        mocks.getCollectionVersion.mockResolvedValue('v1');
        mocks.pickedAnnotationIds.set({});
        mocks.isEditingModeStore.set(false);
    });

    it('renders AnnotationClassificationGridItem for a classification annotation', () => {
        mocks.annotationsData = [buildClassificationAnnotation('cls-1')];

        renderGrid();

        expect(screen.getByTestId('mock-classification-grid-item')).toBeInTheDocument();
        expect(screen.queryByTestId('mock-annotations-grid-item')).not.toBeInTheDocument();
    });

    it('renders AnnotationsGridItem for an OD annotation', () => {
        mocks.annotationsData = [buildOdAnnotation('od-1')];

        renderGrid();

        expect(screen.getByTestId('mock-annotations-grid-item')).toBeInTheDocument();
        expect(screen.queryByTestId('mock-classification-grid-item')).not.toBeInTheDocument();
    });

    it('renders two separate tiles for two classification annotations', () => {
        mocks.annotationsData = [
            buildClassificationAnnotation('cls-1', 'cat'),
            buildClassificationAnnotation('cls-2', 'dog')
        ];

        renderGrid();

        const tiles = screen.getAllByTestId('mock-classification-grid-item');
        expect(tiles).toHaveLength(2);
        expect(tiles[0]).toHaveAttribute('data-annotation-id', 'cls-1');
        expect(tiles[1]).toHaveAttribute('data-annotation-id', 'cls-2');
    });

    it('calls toggleSampleAnnotationCropSelection when a classification tile is clicked', async () => {
        mocks.annotationsData = [buildClassificationAnnotation('cls-1')];

        renderGrid();

        const gridItem = screen.getByTestId('annotation-grid-item');
        await fireEvent.click(gridItem);

        expect(mocks.toggleSampleAnnotationCropSelection).toHaveBeenCalledWith('col-1', 'cls-1');
    });

    it('calls updateAnnotations with the selected classification annotation on bulk relabel', async () => {
        mocks.annotationsData = [buildClassificationAnnotation('cls-1')];
        mocks.pickedAnnotationIds.set({ 'col-1': new Set(['cls-1']) });
        mocks.isEditingModeStore.set(true);

        renderGrid();

        const button = screen.getByTestId('mock-select-label');
        await fireEvent.click(button);

        expect(mocks.updateAnnotations).toHaveBeenCalledWith([
            expect.objectContaining({ annotation_id: 'cls-1', label_name: 'new-label' })
        ]);
    });

    it('populates the undo stack after bulk relabel on a classification selection', async () => {
        mocks.annotationsData = [buildClassificationAnnotation('cls-1')];
        mocks.pickedAnnotationIds.set({ 'col-1': new Set(['cls-1']) });
        mocks.isEditingModeStore.set(true);

        renderGrid();

        const button = screen.getByTestId('mock-select-label');
        await fireEvent.click(button);

        expect(mocks.addReversibleAction).toHaveBeenCalledWith(
            expect.objectContaining({
                description: 'Undo label change for 1 annotation',
                groupId: 'annotation-label-change'
            })
        );
    });
});
