import { render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import TriggerEvaluationDialog from './TriggerEvaluationDialog.svelte';

let annotationCollectionsData: {
    collection_id: string;
    name: string;
    annotation_types: string[];
}[] = [];

vi.mock('$lib/hooks/useAnnotationCollections/useAnnotationCollections', () => ({
    useAnnotationCollections: () => ({ data: annotationCollectionsData })
}));

const triggerMock = vi.fn();
let isPending = false;

vi.mock('./useTriggerEvaluation.svelte', () => ({
    useTriggerEvaluation: () => ({
        mutation: {
            get isPending() {
                return isPending;
            }
        },
        trigger: triggerMock
    })
}));

const defaultProps = {
    datasetId: 'dataset-1',
    collectionId: 'collection-1',
    open: true,
    onOpenChange: vi.fn()
};

describe('TriggerEvaluationDialog', () => {
    beforeEach(() => {
        annotationCollectionsData = [
            { collection_id: 'a', name: 'gt', annotation_types: ['object_detection'] },
            { collection_id: 'b', name: 'pred', annotation_types: ['object_detection'] }
        ];
        triggerMock.mockReset();
        isPending = false;
    });

    it('renders the form with type select, source selects, and a duration note', () => {
        render(TriggerEvaluationDialog, { props: defaultProps });

        expect(
            screen.getByText('Evaluate predictions against ground truth on this dataset.')
        ).toBeInTheDocument();
        expect(screen.getByTestId('evaluation-type-select')).toBeInTheDocument();
        expect(screen.getByTestId('gt-source-select')).toBeInTheDocument();
        expect(screen.getByTestId('pred-source-select')).toBeInTheDocument();
        expect(screen.getByTestId('evaluation-duration-note')).toBeInTheDocument();
    });

    it('shows object-detection config fields by default', () => {
        render(TriggerEvaluationDialog, { props: defaultProps });

        expect(screen.getByTestId('iou-threshold-slider')).toBeInTheDocument();
        expect(screen.getByTestId('classwise-switch')).toBeInTheDocument();
    });

    it('disables the submit button until distinct sources are selected', () => {
        render(TriggerEvaluationDialog, { props: defaultProps });

        expect(screen.getByTestId('trigger-evaluation-submit')).toBeDisabled();
    });

    it('shows an empty state and hides source selects when no source matches the eval type', () => {
        annotationCollectionsData = [
            { collection_id: 'a', name: 'gt', annotation_types: ['classification'] }
        ];
        render(TriggerEvaluationDialog, { props: defaultProps });

        // Default eval type is object_detection; the only source is classification.
        expect(screen.getByTestId('no-matching-sources-warning')).toBeInTheDocument();
        expect(screen.queryByTestId('gt-source-select')).not.toBeInTheDocument();
        expect(screen.getByTestId('trigger-evaluation-submit')).toBeDisabled();
    });
});
