import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { writable } from 'svelte/store';
import BulkAnnotationClass from './BulkAnnotationClass.svelte';

type CountsParams = {
    collectionId: string;
    annotationType?: string;
    countMode?: string;
    filter?: { sample_filter?: Record<string, unknown> };
    enabled?: boolean;
};

const isEditingMode = writable(false);
const selectedSampleIds = writable(new Set<string>());
const lastAnnotationSource = writable<Record<string, string>>({});
const updateLastAnnotationSource = vi.fn();

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        getSelectedSampleIds: () => selectedSampleIds,
        isEditingMode,
        lastAnnotationSource,
        updateLastAnnotationSource
    })
}));

const annotationCollections = { data: [{ collection_id: 'src-1', name: 'annotation' }] };
vi.mock('$lib/hooks/useAnnotationCollections/useAnnotationCollections', () => ({
    useAnnotationCollections: () => annotationCollections
}));

vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: () => ({
        data: [{ annotation_label_id: 'lbl-1', annotation_label_name: 'dog' }]
    })
}));

let countsParams: CountsParams[] = [];
let countsResult: { data?: Array<Record<string, string | number>>; isFetching: boolean } = {
    data: undefined,
    isFetching: false
};
vi.mock('$lib/hooks/useImageAnnotationCounts/useImageAnnotationCounts', () => ({
    useImageAnnotationCountsQueryKey: [{ _id: 'countImageAnnotationsByCollection' }],
    useImageAnnotationCounts: (getParams: () => CountsParams) => {
        countsParams.push(getParams());
        return countsResult;
    }
}));

const addAnnotationClass = vi.fn();
vi.mock('$lib/hooks/useBulkAddAnnotationClass/useBulkAddAnnotationClass', () => ({
    useBulkAddAnnotationClass: () => ({ addAnnotationClass })
}));

const { toast } = vi.hoisted(() => ({ toast: { success: vi.fn(), error: vi.fn() } }));
vi.mock('svelte-sonner', () => ({ toast }));

const applyClass = async (className: string) => {
    const user = userEvent.setup();
    await user.click(screen.getByTestId('bulk-class-picker-trigger'));
    await user.click(await screen.findByTestId(`bulk-class-picker-option-${className}`));
    await user.click(screen.getByTestId('bulk-annotation-class-apply'));
    await user.click(await screen.findByTestId('confirm-apply-submit'));
};

describe('BulkAnnotationClass', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        Element.prototype.scrollIntoView = vi.fn();
        // A confirm dialog left open by an earlier test keeps `pointer-events: none` on the body,
        // which makes every later pointer interaction unperformable.
        document.body.style.pointerEvents = '';
        countsParams = [];
        countsResult = { data: undefined, isFetching: false };
        annotationCollections.data = [{ collection_id: 'src-1', name: 'annotation' }];
        isEditingMode.set(true);
        selectedSampleIds.set(new Set(['s-1', 's-2']));
        lastAnnotationSource.set({});
        addAnnotationClass.mockResolvedValue({
            created_annotation_ids: ['ann-1'],
            created_count: 28,
            skipped_count: 12
        });
    });

    it('is not mounted while editing mode is off', () => {
        isEditingMode.set(false);
        render(BulkAnnotationClass, { props: { collectionId: 'col-1' } });

        expect(screen.queryByTestId('bulk-annotation-class-panel')).not.toBeInTheDocument();
    });

    it('is not mounted without a selection', () => {
        selectedSampleIds.set(new Set());
        render(BulkAnnotationClass, { props: { collectionId: 'col-1' } });

        expect(screen.queryByTestId('bulk-annotation-class-panel')).not.toBeInTheDocument();
    });

    it('shows the selection size and the resolved default annotation source', () => {
        render(BulkAnnotationClass, { props: { collectionId: 'col-1' } });

        expect(screen.getByText('Selected images: 2')).toBeInTheDocument();
        expect(screen.getByTestId('bulk-annotation-class-apply')).toHaveTextContent(
            'Add annotation class to annotation'
        );
    });

    it('counts distinct samples per classification class within the selection and source', () => {
        render(BulkAnnotationClass, { props: { collectionId: 'col-1' } });

        expect(countsParams[0]).toMatchObject({
            collectionId: 'col-1',
            annotationType: 'classification',
            countMode: 'samples',
            enabled: true,
            filter: {
                sample_filter: {
                    sample_ids: ['s-1', 's-2'],
                    annotations_filter: { collection_ids: ['src-1'] }
                }
            }
        });
    });

    it('renders the per-class counts from current_count', () => {
        countsResult = {
            data: [{ label_name: 'dog', current_count: 3, total_count: 900 }],
            isFetching: false
        };
        render(BulkAnnotationClass, { props: { collectionId: 'col-1' } });

        const counts = screen.getByTestId('existing-class-counts');
        expect(counts).toHaveTextContent('dog');
        expect(counts).toHaveTextContent('3');
        expect(counts).not.toHaveTextContent('900');
    });

    it('skips the counts query for an annotation source that does not exist yet', () => {
        lastAnnotationSource.set({ 'col-1': 'brand-new-source' });
        countsResult = {
            data: [{ label_name: 'dog', current_count: 3, total_count: 900 }],
            isFetching: false
        };
        render(BulkAnnotationClass, { props: { collectionId: 'col-1' } });

        expect(countsParams[0]).toMatchObject({ enabled: false, filter: undefined });
        expect(screen.getByTestId('existing-class-counts-empty')).toBeInTheDocument();
    });

    it('remembers a picked annotation source', async () => {
        const user = userEvent.setup();
        render(BulkAnnotationClass, { props: { collectionId: 'col-1' } });

        await user.click(screen.getByTestId('bulk-source-picker-trigger'));
        await user.click(await screen.findByTestId('bulk-source-picker-option-annotation'));

        expect(updateLastAnnotationSource).toHaveBeenCalledWith('col-1', 'annotation');
    });

    it('applies the annotation class to the selection and reports what changed', async () => {
        render(BulkAnnotationClass, { props: { collectionId: 'col-1' } });

        await applyClass('dog');

        expect(addAnnotationClass).toHaveBeenCalledWith({
            className: 'dog',
            annotationSource: 'annotation',
            selectedSampleIds: new Set(['s-1', 's-2'])
        });
        expect(toast.success).toHaveBeenCalledWith(
            'Added to 28 of 40 images; 12 already had this annotation class.'
        );
    });

    it('reports a failed apply', async () => {
        addAnnotationClass.mockRejectedValue(new Error('boom'));
        render(BulkAnnotationClass, { props: { collectionId: 'col-1' } });

        await applyClass('dog');

        expect(toast.error).toHaveBeenCalledWith(
            'Failed to add the annotation class. Please try again.'
        );
    });
});
