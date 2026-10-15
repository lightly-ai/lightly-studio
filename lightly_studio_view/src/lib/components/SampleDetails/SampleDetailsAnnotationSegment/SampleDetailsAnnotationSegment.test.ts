import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { render, screen, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SampleDetailsAnnotationSegment from './SampleDetailsAnnotationSegment.svelte';
import { useAnnotationSourceGroupState } from './useAnnotationSourceGroupState';

const mocks = vi.hoisted(() => ({
    collections: [] as { collection_id: string; name: string }[],
    selectedCollectionIds: [] as string[],
    lastCreatedAnnotationId: null as string | null,
    enforceColoringByClassStore: undefined as unknown as { set: (value: boolean) => void },
    isEditingMode: undefined as unknown as { set: (value: boolean) => void },
    userRole: 'labeler' as string | undefined
}));

// Replace the heavy per-annotation row with a lightweight stub.
vi.mock(
    '../SampleDetailsSidePanel/SampleDetailsSidePanelAnnotation/SampleDetailsSidePanelAnnotation.svelte',
    async () => {
        const module =
            await import('../SampleDetailsSidePanel/SampleDetailsSidePanelAnnotation/SampleDetailsSidePanelAnnotation.mock.svelte');
        return { default: module.default };
    }
);

vi.mock('$lib/hooks/useAnnotationCollections/useAnnotationCollections', () => ({
    useAnnotationCollections: vi.fn(() => ({ data: mocks.collections }))
}));

vi.mock('$lib/hooks/useAnnotationCollectionsFilter/useAnnotationCollectionsFilter', async () => {
    const { readable } = await import('svelte/store');
    return {
        useAnnotationCollectionsFilter: vi.fn(() => ({
            selectedCollectionIds: readable(mocks.selectedCollectionIds),
            isSourceVisible: readable((sourceId: string) =>
                mocks.selectedCollectionIds.includes(sourceId)
            )
        }))
    };
});

vi.mock('$lib/hooks/useAuth/useAuth', () => ({
    default: () => ({ user: mocks.userRole ? { role: mocks.userRole } : undefined })
}));

vi.mock('$lib/hooks/useGlobalStorage', async () => {
    const { writable } = await import('svelte/store');
    const isEditingMode = writable(false);
    mocks.isEditingMode = isEditingMode;
    return {
        useGlobalStorage: vi.fn(() => ({
            addReversibleAction: vi.fn(),
            updateLastAnnotationLabel: vi.fn(),
            isEditingMode
        }))
    };
});

vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: vi.fn(() => ({
        context: {
            annotationId: null,
            lockedAnnotationIds: new Set<string>(),
            lastCreatedAnnotationId: mocks.lastCreatedAnnotationId,
            annotationType: null
        },
        setAnnotationId: vi.fn(),
        setAnnotationLabel: vi.fn(),
        setLastCreatedAnnotationId: vi.fn(),
        setLockedAnnotationIds: vi.fn()
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

vi.mock('$lib/hooks/useAnnotationSelection/useAnnotationSelection', () => ({
    useAnnotationSelection: vi.fn(() => ({ selectAnnotation: vi.fn() }))
}));

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

const groundTruthSource = { collection_id: 'source-gt', name: 'Ground truth' };
const predictionsSource = { collection_id: 'source-pred', name: 'Predictions' };

const createAnnotation = (sampleId: string, sourceId: string, labelName: string): AnnotationView =>
    ({
        parent_sample_id: 'parent-sample-1',
        sample_id: sampleId,
        annotation_collection_id: sourceId,
        annotation_type: 'object_detection',
        annotation_label: { annotation_label_name: labelName },
        created_at: new Date('1970-01-01T00:00:00.000Z'),
        object_detection_details: { x: 0, y: 0, width: 10, height: 10 }
    }) satisfies AnnotationView;

const defaultProps = {
    annotationsIdsToHide: new Set<string>(),
    collectionId: 'collection-1',
    sampleId: 'sample-1',
    annotations: [] as AnnotationView[],
    isPanModeEnabled: false,
    refetch: vi.fn()
};

const getRow = (annotationId: string) => {
    const row = screen
        .getAllByTestId('mock-annotation-row')
        .find((row) => row.getAttribute('data-annotation-id') === annotationId);
    expect(row).toBeDefined();
    return row!;
};

describe('SampleDetailsAnnotationSegment', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.collections = [];
        mocks.selectedCollectionIds = [];
        mocks.lastCreatedAnnotationId = null;
        mocks.enforceColoringByClassStore.set(false);
        mocks.isEditingMode.set(false);
        mocks.userRole = 'labeler';
        useAnnotationSourceGroupState().sourceGroupStates.set({});
    });

    it('renders a flat list without source groups when there is a single source', () => {
        mocks.collections = [groundTruthSource];
        const annotations = [
            createAnnotation('a1', groundTruthSource.collection_id, 'cat'),
            createAnnotation('a2', groundTruthSource.collection_id, 'dog')
        ];

        render(SampleDetailsAnnotationSegment, { props: { ...defaultProps, annotations } });

        expect(screen.getAllByTestId('mock-annotation-row')).toHaveLength(2);
        expect(screen.queryByTestId('annotation-source-group-header')).not.toBeInTheDocument();
        expect(screen.queryByText(groundTruthSource.name)).not.toBeInTheDocument();
    });

    it('groups annotations under one header per source when there are multiple sources', () => {
        mocks.collections = [groundTruthSource, predictionsSource];
        mocks.selectedCollectionIds = [
            groundTruthSource.collection_id,
            predictionsSource.collection_id
        ];
        const annotations = [
            createAnnotation('a1', groundTruthSource.collection_id, 'cat'),
            createAnnotation('a2', predictionsSource.collection_id, 'zebra'),
            createAnnotation('a3', groundTruthSource.collection_id, 'dog')
        ];

        render(SampleDetailsAnnotationSegment, { props: { ...defaultProps, annotations } });

        const headers = screen.getAllByTestId('annotation-source-group-header');
        expect(headers).toHaveLength(2);
        expect(headers[0]).toHaveTextContent(groundTruthSource.name);
        expect(headers[0]).toHaveTextContent('2');
        expect(headers[1]).toHaveTextContent(predictionsSource.name);
        expect(headers[1]).toHaveTextContent('1');
        expect(screen.getAllByTestId('mock-annotation-row')).toHaveLength(3);
    });

    it('excludes classification annotations from the source groups', () => {
        mocks.collections = [groundTruthSource, predictionsSource];
        mocks.selectedCollectionIds = [
            groundTruthSource.collection_id,
            predictionsSource.collection_id
        ];
        const annotations = [
            createAnnotation('a1', groundTruthSource.collection_id, 'cat'),
            {
                ...createAnnotation('a2', predictionsSource.collection_id, 'zebra'),
                annotation_type: 'classification' as const,
                object_detection_details: undefined
            }
        ];

        render(SampleDetailsAnnotationSegment, { props: { ...defaultProps, annotations } });

        const headers = screen.getAllByTestId('annotation-source-group-header');
        expect(headers).toHaveLength(1);
        expect(headers[0]).toHaveTextContent(groundTruthSource.name);
        expect(screen.getAllByTestId('mock-annotation-row')).toHaveLength(1);
    });

    describe('source visibility toggle', () => {
        beforeEach(() => {
            mocks.collections = [groundTruthSource, predictionsSource];
            mocks.selectedCollectionIds = [
                groundTruthSource.collection_id,
                predictionsSource.collection_id
            ];
        });

        const annotations = [
            createAnnotation('gt-1', groundTruthSource.collection_id, 'cat'),
            createAnnotation('gt-2', groundTruthSource.collection_id, 'dog'),
            createAnnotation('pred-1', predictionsSource.collection_id, 'cat')
        ];

        it('hides and shows all annotations of a source when clicking its eye', async () => {
            const user = userEvent.setup();
            render(SampleDetailsAnnotationSegment, { props: { ...defaultProps, annotations } });

            // Groups are rendered in source order: Ground truth first.
            await user.click(screen.getAllByTestId('source-group-eye')[0]);

            expect(getRow('gt-1')).toHaveAttribute('data-hidden', 'true');
            expect(getRow('gt-2')).toHaveAttribute('data-hidden', 'true');
            expect(getRow('pred-1')).not.toHaveAttribute('data-hidden', 'true');
            expect(screen.getAllByTestId('source-group-eye-off')).toHaveLength(1);

            await user.click(screen.getByTestId('source-group-eye-off'));

            expect(getRow('gt-1')).not.toHaveAttribute('data-hidden', 'true');
            expect(getRow('gt-2')).not.toHaveAttribute('data-hidden', 'true');
            expect(screen.queryByTestId('source-group-eye-off')).not.toBeInTheDocument();
        });

        it('flips the source eye depending on whether all of its annotations are hidden', async () => {
            const user = userEvent.setup();
            render(SampleDetailsAnnotationSegment, { props: { ...defaultProps, annotations } });

            // Hide both Ground truth annotations through their row toggles.
            await user.click(within(getRow('gt-1')).getByTestId('mock-annotation-row-toggle'));
            await user.click(within(getRow('gt-2')).getByTestId('mock-annotation-row-toggle'));

            expect(screen.getAllByTestId('source-group-eye-off')).toHaveLength(1);

            // Showing a single annotation again flips the source eye back to open.
            await user.click(within(getRow('gt-1')).getByTestId('mock-annotation-row-toggle'));

            expect(screen.queryByTestId('source-group-eye-off')).not.toBeInTheDocument();
            expect(screen.getAllByTestId('source-group-eye')).toHaveLength(2);
        });
    });

    describe('seeding from the grid source filter', () => {
        const annotations = [
            createAnnotation('gt-1', groundTruthSource.collection_id, 'cat'),
            createAnnotation('pred-1', predictionsSource.collection_id, 'cat'),
            createAnnotation('pred-2', predictionsSource.collection_id, 'dog')
        ];

        beforeEach(() => {
            mocks.collections = [groundTruthSource, predictionsSource];
        });

        it('collapses an unselected source and keeps its annotations hidden', async () => {
            const user = userEvent.setup();
            mocks.selectedCollectionIds = [groundTruthSource.collection_id];

            render(SampleDetailsAnnotationSegment, { props: { ...defaultProps, annotations } });

            // The selected source stays expanded; the unselected Predictions group starts
            // collapsed (its rows are not rendered) but still shows a closed eye.
            const visibleRowIds = () =>
                screen
                    .queryAllByTestId('mock-annotation-row')
                    .map((row) => row.getAttribute('data-annotation-id'));
            expect(visibleRowIds()).toEqual(['gt-1']);
            expect(getRow('gt-1')).not.toHaveAttribute('data-hidden', 'true');
            expect(screen.getAllByTestId('source-group-eye-off')).toHaveLength(1);

            // Expanding the collapsed group reveals its annotations, which are hidden.
            await user.click(screen.getByText(predictionsSource.name));
            expect(getRow('pred-1')).toHaveAttribute('data-hidden', 'true');
            expect(getRow('pred-2')).toHaveAttribute('data-hidden', 'true');
        });

        it('keeps a freshly created source expanded even though it is unselected', () => {
            // Predictions is unselected on the grid, so it would normally seed collapsed...
            mocks.selectedCollectionIds = [groundTruthSource.collection_id];
            // ...but the user just created an annotation in it, so its group stays open.
            mocks.lastCreatedAnnotationId = 'pred-1';

            render(SampleDetailsAnnotationSegment, { props: { ...defaultProps, annotations } });

            const visibleRowIds = screen
                .queryAllByTestId('mock-annotation-row')
                .map((row) => row.getAttribute('data-annotation-id'));
            expect(visibleRowIds).toContain('pred-1');
            expect(visibleRowIds).toContain('pred-2');
        });

        it('keeps a seeded-hidden source expanded after the user expands it', async () => {
            const user = userEvent.setup();
            mocks.selectedCollectionIds = [groundTruthSource.collection_id];

            const { rerender } = render(SampleDetailsAnnotationSegment, {
                props: { ...defaultProps, annotations }
            });

            // Expand the initially collapsed Predictions group on the first sample.
            await user.click(screen.getByText(predictionsSource.name));
            expect(getRow('pred-1')).toBeDefined();

            // The next sample keeps the group expanded, and its annotations stay hidden.
            await rerender({ ...defaultProps, annotations, sampleId: 'sample-2' });

            expect(getRow('pred-1')).toHaveAttribute('data-hidden', 'true');
            expect(getRow('pred-2')).toHaveAttribute('data-hidden', 'true');
        });

        it('shows a seeded-hidden source on the next sample after the user shows it', async () => {
            const user = userEvent.setup();
            mocks.selectedCollectionIds = [groundTruthSource.collection_id];

            const { rerender } = render(SampleDetailsAnnotationSegment, {
                props: { ...defaultProps, annotations }
            });

            await user.click(screen.getByTestId('source-group-eye-off'));

            const nextAnnotations = [
                createAnnotation('gt-9', groundTruthSource.collection_id, 'cat'),
                createAnnotation('pred-9', predictionsSource.collection_id, 'cat')
            ];
            await rerender({ ...defaultProps, annotations: nextAnnotations, sampleId: 'sample-2' });

            // The shown source is visible, and its untouched collapse keeps the grid default.
            expect(screen.queryByTestId('source-group-eye-off')).not.toBeInTheDocument();
            await user.click(screen.getByText(predictionsSource.name));
            expect(getRow('pred-9')).not.toHaveAttribute('data-hidden', 'true');
        });

        it('starts with all annotations visible when all sources are selected', () => {
            mocks.selectedCollectionIds = [
                groundTruthSource.collection_id,
                predictionsSource.collection_id
            ];

            render(SampleDetailsAnnotationSegment, { props: { ...defaultProps, annotations } });

            expect(getRow('gt-1')).not.toHaveAttribute('data-hidden', 'true');
            expect(getRow('pred-1')).not.toHaveAttribute('data-hidden', 'true');
            expect(screen.queryByTestId('source-group-eye-off')).not.toBeInTheDocument();
        });

        it('hides every annotation when the grid has no source selected', async () => {
            const user = userEvent.setup();
            mocks.selectedCollectionIds = [];

            render(SampleDetailsAnnotationSegment, { props: { ...defaultProps, annotations } });

            // Both groups seed fully hidden, so both start collapsed with a closed eye.
            expect(screen.queryAllByTestId('mock-annotation-row')).toHaveLength(0);
            expect(screen.getAllByTestId('source-group-eye-off')).toHaveLength(2);

            await user.click(screen.getByText(groundTruthSource.name));
            expect(getRow('gt-1')).toHaveAttribute('data-hidden', 'true');
        });

        it('seeds once the annotations become available', async () => {
            const user = userEvent.setup();
            mocks.selectedCollectionIds = [groundTruthSource.collection_id];

            const { rerender } = render(SampleDetailsAnnotationSegment, {
                props: { ...defaultProps, annotations: [] }
            });

            await rerender({ annotations });

            expect(getRow('gt-1')).not.toHaveAttribute('data-hidden', 'true');
            // Predictions is seeded hidden, so its group starts collapsed; expand to inspect.
            await user.click(screen.getByText(predictionsSource.name));
            expect(getRow('pred-1')).toHaveAttribute('data-hidden', 'true');
            expect(getRow('pred-2')).toHaveAttribute('data-hidden', 'true');
        });
    });

    describe('keeping the source state across samples', () => {
        beforeEach(() => {
            mocks.collections = [groundTruthSource, predictionsSource];
            mocks.selectedCollectionIds = [
                groundTruthSource.collection_id,
                predictionsSource.collection_id
            ];
        });

        const firstAnnotations = [
            createAnnotation('gt-1', groundTruthSource.collection_id, 'cat'),
            createAnnotation('pred-1', predictionsSource.collection_id, 'cat')
        ];
        const nextAnnotations = [
            createAnnotation('gt-2', groundTruthSource.collection_id, 'dog'),
            createAnnotation('pred-2', predictionsSource.collection_id, 'dog')
        ];

        it('keeps collapsed and hidden sources on the next sample', async () => {
            const user = userEvent.setup();
            const { rerender } = render(SampleDetailsAnnotationSegment, {
                props: { ...defaultProps, annotations: firstAnnotations }
            });

            // The QA flow: collapse both groups, then hide Predictions.
            await user.click(screen.getByText(groundTruthSource.name));
            await user.click(screen.getByText(predictionsSource.name));
            await user.click(screen.getAllByTestId('source-group-eye')[1]);

            // A sample without Predictions in between must not reset its state.
            await rerender({
                ...defaultProps,
                annotations: [createAnnotation('gt-3', groundTruthSource.collection_id, 'cat')],
                sampleId: 'sample-2'
            });
            await rerender({ ...defaultProps, annotations: nextAnnotations, sampleId: 'sample-3' });

            expect(screen.queryAllByTestId('mock-annotation-row')).toHaveLength(0);
            expect(screen.getAllByTestId('source-group-eye')).toHaveLength(1);
            expect(screen.getAllByTestId('source-group-eye-off')).toHaveLength(1);

            await user.click(screen.getByText(groundTruthSource.name));
            await user.click(screen.getByText(predictionsSource.name));
            expect(getRow('gt-2')).not.toHaveAttribute('data-hidden', 'true');
            expect(getRow('pred-2')).toHaveAttribute('data-hidden', 'true');
        });

        it('expands a collapsed source when the user creates its first annotation', async () => {
            const user = userEvent.setup();
            // The mocked label context is read at mount, so the new annotation's ID is set now.
            mocks.lastCreatedAnnotationId = 'pred-new';
            const { rerender } = render(SampleDetailsAnnotationSegment, {
                props: { ...defaultProps, annotations: firstAnnotations }
            });

            await user.click(screen.getByText(predictionsSource.name));
            const groundTruthOnly = [
                createAnnotation('gt-2', groundTruthSource.collection_id, 'dog')
            ];
            await rerender({ ...defaultProps, annotations: groundTruthOnly, sampleId: 'sample-2' });
            await rerender({
                ...defaultProps,
                annotations: [
                    ...groundTruthOnly,
                    createAnnotation('pred-new', predictionsSource.collection_id, 'cat')
                ],
                sampleId: 'sample-2'
            });

            expect(getRow('pred-new')).toBeDefined();
        });

        it('keeps the default state of untouched sources', async () => {
            const user = userEvent.setup();
            const { rerender } = render(SampleDetailsAnnotationSegment, {
                props: { ...defaultProps, annotations: firstAnnotations }
            });

            await user.click(screen.getByText(groundTruthSource.name));
            await rerender({ ...defaultProps, annotations: nextAnnotations, sampleId: 'sample-2' });

            expect(screen.queryAllByTestId('mock-annotation-row')).toHaveLength(1);
            expect(getRow('pred-2')).not.toHaveAttribute('data-hidden', 'true');
        });
    });

    describe('coloring by visible sources', () => {
        const annotations = [
            createAnnotation('gt-1', groundTruthSource.collection_id, 'cat'),
            createAnnotation('pred-1', predictionsSource.collection_id, 'cat')
        ];

        const getSourceColorMarker = (header: HTMLElement) =>
            header.querySelector('span[style*="background-color"]');

        beforeEach(() => {
            mocks.collections = [groundTruthSource, predictionsSource];
            mocks.selectedCollectionIds = [
                groundTruthSource.collection_id,
                predictionsSource.collection_id
            ];
        });

        it('colors by source only while annotations from multiple sources are visible', async () => {
            const user = userEvent.setup();
            render(SampleDetailsAnnotationSegment, { props: { ...defaultProps, annotations } });

            // Both sources visible: source color markers in the headers, no label
            // legends in the rows.
            let headers = screen.getAllByTestId('annotation-source-group-header');
            expect(getSourceColorMarker(headers[0])).toBeInTheDocument();
            expect(getSourceColorMarker(headers[1])).toBeInTheDocument();
            expect(getRow('gt-1')).toHaveAttribute('data-color-by-source', 'true');

            // Hiding one source leaves a single visible source: label colors again.
            await user.click(screen.getAllByTestId('source-group-eye')[1]);

            headers = screen.getAllByTestId('annotation-source-group-header');
            expect(getSourceColorMarker(headers[0])).not.toBeInTheDocument();
            expect(getSourceColorMarker(headers[1])).not.toBeInTheDocument();
            expect(getRow('gt-1')).toHaveAttribute('data-color-by-source', 'false');
        });

        it('uses class colors when enforce coloring by class is enabled, even with multiple visible sources', () => {
            mocks.enforceColoringByClassStore.set(true);

            render(SampleDetailsAnnotationSegment, { props: { ...defaultProps, annotations } });

            // Source color markers must be hidden even though both sources are visible.
            const headers = screen.getAllByTestId('annotation-source-group-header');
            expect(getSourceColorMarker(headers[0])).not.toBeInTheDocument();
            expect(getSourceColorMarker(headers[1])).not.toBeInTheDocument();
            // Rows receive class-based coloring (colorBySource = false).
            expect(getRow('gt-1')).toHaveAttribute('data-color-by-source', 'false');
            expect(getRow('pred-1')).toHaveAttribute('data-color-by-source', 'false');
        });
    });

    describe('empty state copy', () => {
        it('shows toolbar guidance when in editing mode and there are no annotations', () => {
            mocks.isEditingMode.set(true);
            render(SampleDetailsAnnotationSegment, { props: defaultProps });

            expect(screen.getByTestId('empty-state-message')).toHaveTextContent(
                'No annotations. Use the toolbar to add one.'
            );
        });

        it('shows edit guidance for users who can edit when there are no annotations', () => {
            mocks.userRole = 'labeler';
            render(SampleDetailsAnnotationSegment, { props: defaultProps });

            expect(screen.getByTestId('empty-state-message')).toHaveTextContent(
                'No annotations. Click Edit annotations and use the toolbar.'
            );
        });

        it('shows plain "No annotations." without edit guidance for viewer role', () => {
            mocks.userRole = 'viewer';
            render(SampleDetailsAnnotationSegment, { props: defaultProps });

            expect(screen.getByTestId('empty-state-message')).toHaveTextContent('No annotations.');
        });
    });
});
