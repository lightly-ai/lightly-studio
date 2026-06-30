import { render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import TriggerEvaluationDialog from './TriggerEvaluationDialog.svelte';

let annotationCollectionsData: { collection_id: string; name: string }[] = [];

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
            { collection_id: 'a', name: 'gt' },
            { collection_id: 'b', name: 'pred' }
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
});
