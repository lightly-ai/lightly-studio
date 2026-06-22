import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SampleDetailsClassificationSegment from './SampleDetailsClassificationSegment.svelte';

const mocks = vi.hoisted(() => ({
    collections: [] as { collection_id: string; name: string }[],
    selectedCollectionIds: [] as string[],
    lastCreatedAnnotationId: null as string | null,
    isEditingMode: undefined as unknown as { set: (value: boolean) => void },
    enforceColoringByClassStore: undefined as unknown as { set: (value: boolean) => void }
}));

vi.mock('$app/state', () => ({
    page: { params: { dataset_id: 'dataset-1' } }
}));

// The classification segment imports useAnnotationCollections through the `$lib/hooks`
// barrel; mocking the underlying module replaces the barrel re-export too.
vi.mock('$lib/hooks/useAnnotationCollections/useAnnotationCollections', () => ({
    useAnnotationCollections: vi.fn(() => ({ data: mocks.collections }))
}));

// Drives the grid-filter seeded collapse: sources missing from the selection start collapsed.
vi.mock('$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter', async () => {
    const { readable } = await import('svelte/store');
    return {
        useAnnotationCollectionsFilter: vi.fn(() => ({
            selectedCollectionIds: readable(mocks.selectedCollectionIds)
        }))
    };
});

vi.mock('$lib/hooks/useGlobalStorage', async () => {
    const { writable } = await import('svelte/store');
    const isEditingMode = writable(false);
    mocks.isEditingMode = isEditingMode;
    return {
        useGlobalStorage: () => ({
            isEditingMode,
            addReversibleAction: vi.fn()
        })
    };
});

vi.mock('$lib/hooks/useSettings', async () => {
    const { writable } = await import('svelte/store');
    const enforceColoringByClassStore = writable(false);
    mocks.enforceColoringByClassStore = enforceColoringByClassStore;
    return {
        useSettings: vi.fn(() => ({
            enforceColoringByClassStore
        }))
    };
});

// The component reads annotationLabelContext (annotationSource to tag a new classification's
// source, lastCreatedAnnotationId to keep its group expanded) and sets the last created id on
// create; the real hook throws when rendered without a provider.
vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: vi.fn(() => ({
        context: {
            annotationSource: null,
            lastCreatedAnnotationId: mocks.lastCreatedAnnotationId
        },
        setLastCreatedAnnotationId: vi.fn()
    }))
}));

vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: vi.fn(() => ({ data: [] }))
}));

vi.mock('$lib/hooks/useCreateAnnotation/useCreateAnnotation', () => ({
    useCreateAnnotation: vi.fn(() => ({ createAnnotation: vi.fn() }))
}));

vi.mock('$lib/hooks/useDeleteAnnotation/useDeleteAnnotation', () => ({
    useDeleteAnnotation: vi.fn(() => ({ deleteAnnotation: vi.fn() }))
}));

vi.mock('$lib/hooks/useCreateLabel/useCreateLabel', () => ({
    useCreateLabel: vi.fn(() => ({ createLabel: vi.fn() }))
}));

vi.mock('$lib/hooks/useUpdateAnnotationsMutation/useUpdateAnnotationsMutation', () => ({
    useUpdateAnnotationsMutation: vi.fn(() => ({ updateAnnotations: vi.fn() }))
}));

vi.mock('$lib/hooks/useCollection/useCollection', () => ({
    useCollectionWithChildren: vi.fn(() => ({ refetch: vi.fn() }))
}));

vi.mock('svelte-sonner', () => ({
    toast: { success: vi.fn(), error: vi.fn() }
}));

vi.mock('$lib/hooks/useCustomLabelColors', async () => {
    const { writable } = await import('svelte/store');
    return {
        useCustomLabelColors: () => ({
            customLabelColorsStore: writable({}),
            getCustomColor: () => undefined,
            setCustomColor: vi.fn(),
            hasCustomColor: () => false
        })
    };
});

const groundTruthSource = { collection_id: 'source-gt', name: 'Ground truth' };
const predictionsSource = { collection_id: 'source-pred', name: 'Predictions' };

const createClassification = (
    sampleId: string,
    sourceId: string,
    labelName: string,
    confidence?: number | null
): AnnotationView =>
    ({
        parent_sample_id: 'parent-sample-1',
        sample_id: sampleId,
        annotation_collection_id: sourceId,
        annotation_type: 'classification',
        annotation_label: { annotation_label_name: labelName },
        created_at: new Date('1970-01-01T00:00:00.000Z'),
        confidence
    }) satisfies AnnotationView;

const defaultProps = {
    collectionId: 'collection-1',
    sampleId: 'sample-1',
    annotations: [] as AnnotationView[],
    refetch: vi.fn()
};

describe('SampleDetailsClassificationSegment', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.collections = [];
        mocks.selectedCollectionIds = [];
        mocks.lastCreatedAnnotationId = null;
        mocks.isEditingMode.set(false);
        mocks.enforceColoringByClassStore.set(false);
    });

    it('renders a flat list without source groups for a single source', () => {
        mocks.collections = [groundTruthSource];
        const annotations = [
            createClassification('c1', groundTruthSource.collection_id, 'bird'),
            createClassification('c2', groundTruthSource.collection_id, 'cat')
        ];

        render(SampleDetailsClassificationSegment, { props: { ...defaultProps, annotations } });

        expect(screen.queryByTestId('annotation-source-group-header')).not.toBeInTheDocument();
        expect(screen.getByText('bird')).toBeInTheDocument();
        expect(screen.getByText('cat')).toBeInTheDocument();
    });

    it('groups classifications under one header per source for multiple sources', () => {
        mocks.collections = [groundTruthSource, predictionsSource];
        const annotations = [
            createClassification('c1', groundTruthSource.collection_id, 'cat'),
            createClassification('c2', predictionsSource.collection_id, 'zebra'),
            createClassification('c3', groundTruthSource.collection_id, 'dog')
        ];

        render(SampleDetailsClassificationSegment, { props: { ...defaultProps, annotations } });

        const headers = screen.getAllByTestId('annotation-source-group-header');
        expect(headers).toHaveLength(2);
        expect(headers[0]).toHaveTextContent(groundTruthSource.name);
        expect(headers[0]).toHaveTextContent('2');
        expect(headers[1]).toHaveTextContent(predictionsSource.name);
        expect(headers[1]).toHaveTextContent('1');
        expect(screen.getByText('zebra')).toBeInTheDocument();
    });

    it('never shows the visibility eye on classification groups', () => {
        mocks.collections = [groundTruthSource, predictionsSource];
        const annotations = [
            createClassification('c1', groundTruthSource.collection_id, 'cat'),
            createClassification('c2', predictionsSource.collection_id, 'zebra')
        ];

        render(SampleDetailsClassificationSegment, { props: { ...defaultProps, annotations } });

        expect(screen.getAllByTestId('annotation-source-group-header')).toHaveLength(2);
        expect(screen.queryByTestId('source-group-eye')).not.toBeInTheDocument();
        expect(screen.queryByTestId('source-group-eye-off')).not.toBeInTheDocument();
    });

    it('collapses a source left unselected on the grid', () => {
        mocks.collections = [groundTruthSource, predictionsSource];
        mocks.selectedCollectionIds = [groundTruthSource.collection_id];
        const annotations = [
            createClassification('c1', groundTruthSource.collection_id, 'cat'),
            createClassification('c2', predictionsSource.collection_id, 'zebra')
        ];

        render(SampleDetailsClassificationSegment, { props: { ...defaultProps, annotations } });

        // Both headers render, but the unselected Predictions group starts collapsed,
        // hiding its classifications; the selected Ground truth group stays expanded.
        expect(screen.getAllByTestId('annotation-source-group-header')).toHaveLength(2);
        expect(screen.getByText('cat')).toBeInTheDocument();
        expect(screen.queryByText('zebra')).not.toBeInTheDocument();
    });

    it('keeps a freshly created source expanded even though it is unselected', () => {
        // Predictions is unselected on the grid, so it would normally seed collapsed...
        mocks.collections = [groundTruthSource, predictionsSource];
        mocks.selectedCollectionIds = [groundTruthSource.collection_id];
        // ...but the user just created this classification in it, so its group stays open.
        mocks.lastCreatedAnnotationId = 'c2';
        const annotations = [
            createClassification('c1', groundTruthSource.collection_id, 'cat'),
            createClassification('c2', predictionsSource.collection_id, 'zebra')
        ];

        render(SampleDetailsClassificationSegment, { props: { ...defaultProps, annotations } });

        expect(screen.getByText('zebra')).toBeInTheDocument();
    });

    it('expands a collapsed source when its header is clicked', async () => {
        const user = userEvent.setup();
        mocks.collections = [groundTruthSource, predictionsSource];
        mocks.selectedCollectionIds = [groundTruthSource.collection_id];
        const annotations = [
            createClassification('c1', groundTruthSource.collection_id, 'cat'),
            createClassification('c2', predictionsSource.collection_id, 'zebra')
        ];

        render(SampleDetailsClassificationSegment, { props: { ...defaultProps, annotations } });

        expect(screen.queryByText('zebra')).not.toBeInTheDocument();

        await user.click(screen.getByText(predictionsSource.name));

        expect(screen.getByText('zebra')).toBeInTheDocument();
    });

    it('shows confidence value when present', () => {
        mocks.collections = [groundTruthSource];
        const annotations = [
            createClassification('c1', groundTruthSource.collection_id, 'bird', 0.95)
        ];

        render(SampleDetailsClassificationSegment, { props: { ...defaultProps, annotations } });

        expect(screen.getByText('bird')).toBeInTheDocument();
        expect(screen.getByText('Confidence: 0.95')).toBeInTheDocument();
    });

    it('does not show confidence line when confidence is null', () => {
        mocks.collections = [groundTruthSource];
        const annotations = [
            createClassification('c1', groundTruthSource.collection_id, 'bird', null)
        ];

        render(SampleDetailsClassificationSegment, { props: { ...defaultProps, annotations } });

        expect(screen.getByText('bird')).toBeInTheDocument();
        expect(screen.queryByText(/Confidence:/)).not.toBeInTheDocument();
    });

    it('shows source group color markers when multiple sources are visible and enforce coloring is disabled', () => {
        mocks.collections = [groundTruthSource, predictionsSource];
        mocks.enforceColoringByClassStore.set(false);
        const annotations = [
            createClassification('c1', groundTruthSource.collection_id, 'cat'),
            createClassification('c2', predictionsSource.collection_id, 'zebra')
        ];

        render(SampleDetailsClassificationSegment, { props: { ...defaultProps, annotations } });

        expect(screen.getByTestId(`color-marker-${groundTruthSource.name}`)).toBeInTheDocument();
        expect(screen.getByTestId(`color-marker-${predictionsSource.name}`)).toBeInTheDocument();
    });

    it('hides source group color markers when enforce coloring by class is enabled', () => {
        mocks.collections = [groundTruthSource, predictionsSource];
        mocks.enforceColoringByClassStore.set(true);
        const annotations = [
            createClassification('c1', groundTruthSource.collection_id, 'cat'),
            createClassification('c2', predictionsSource.collection_id, 'zebra')
        ];

        render(SampleDetailsClassificationSegment, { props: { ...defaultProps, annotations } });

        expect(
            screen.queryByTestId(`color-marker-${groundTruthSource.name}`)
        ).not.toBeInTheDocument();
        expect(
            screen.queryByTestId(`color-marker-${predictionsSource.name}`)
        ).not.toBeInTheDocument();
    });

    it('renders editable rows inside groups with a single add button below', async () => {
        const user = userEvent.setup();
        mocks.isEditingMode.set(true);
        mocks.collections = [groundTruthSource, predictionsSource];
        const annotations = [
            createClassification('c1', groundTruthSource.collection_id, 'cat'),
            createClassification('c2', predictionsSource.collection_id, 'zebra'),
            createClassification('c3', groundTruthSource.collection_id, 'dog')
        ];

        render(SampleDetailsClassificationSegment, { props: { ...defaultProps, annotations } });

        expect(screen.getAllByTestId('annotation-source-group-header')).toHaveLength(2);
        // One editable combobox per classification, rendered inside the groups.
        expect(screen.getAllByRole('combobox')).toHaveLength(3);
        // The add button is rendered once, below the groups (not duplicated per group).
        expect(screen.getAllByTestId('add-classification-button')).toHaveLength(1);

        // Adding a draft renders an extra editable row without duplicating the add button.
        await user.click(screen.getByTestId('add-classification-button'));
        expect(screen.getAllByRole('combobox')).toHaveLength(4);
        expect(screen.getAllByTestId('add-classification-button')).toHaveLength(1);
    });
});
