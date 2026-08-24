import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { get } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useClassifierState } from '$lib/hooks/useClassifiers/useClassifierState';
import { useClassifierWorkflow } from '$lib/hooks/useClassifiers/useClassifierWorkflow';
import RefineClassifierDialog from './RefineClassifierDialog.svelte';

const mocks = vi.hoisted(() => ({
    applyClassifierCorrections: vi.fn(),
    commitTempClassifier: vi.fn(),
    refineClassifier: vi.fn(),
    showClassifierTrainingSamples: vi.fn()
}));

vi.mock('$app/state', () => ({
    page: { params: { collection_id: 'collection-id' } }
}));

vi.mock('$lib/hooks/useClassifiers/useClassifiers', () => ({
    useClassifiers: () => mocks
}));

vi.mock('$lib/hooks/useClassifiers/useClassifiersMenu', () => ({
    useClassifiersMenu: () => ({
        openClassifiersMenu: vi.fn(),
        switchToManageTab: vi.fn(),
        scrollToAndSelectClassifier: vi.fn()
    })
}));

vi.mock('./ClassifierSamplesGrid.svelte', () => ({
    default: vi.fn()
}));

describe('RefineClassifierDialog', () => {
    const classifierState = useClassifierState();
    const classifierWorkflow = useClassifierWorkflow();

    beforeEach(() => {
        vi.resetAllMocks();
        mocks.applyClassifierCorrections.mockResolvedValue(undefined);
        mocks.commitTempClassifier.mockResolvedValue(undefined);
        mocks.refineClassifier.mockResolvedValue(undefined);
        mocks.showClassifierTrainingSamples.mockResolvedValue(undefined);
        classifierWorkflow.close();
        classifierWorkflow.openRefine('existing', 'classifier-id', 'Zebras', [
            'positive',
            'negative'
        ]);
        classifierState.classifierSamples.set({
            positiveSampleIds: ['p1', 'p2'],
            negativeSampleIds: ['n1', 'n2']
        });
        classifierState.classifierSelectedSampleIds.set(new Set(['p1', 'n1']));
    });

    it('records a successful review', async () => {
        render(RefineClassifierDialog, { onCancel: vi.fn(), onFinish: vi.fn() });

        expect(screen.getByText('Review a batch to estimate agreement.')).toBeInTheDocument();

        await fireEvent.click(screen.getByRole('button', { name: 'Apply Corrections & Continue' }));

        await waitFor(() => {
            expect(get(classifierWorkflow.workflow)).toMatchObject({
                confirmedPredictions: 2,
                reviewedSamples: 4,
                latestConfirmedPredictions: 2,
                latestReviewedSamples: 4
            });
        });
        expect(screen.getByText(/Overall review agreement: 50%/)).toBeInTheDocument();
        expect(screen.getByText(/2 of 4 predictions confirmed/)).toBeInTheDocument();
    });

    it('orders visible actions by hierarchy and styles finish as primary', () => {
        render(RefineClassifierDialog, { onCancel: vi.fn(), onFinish: vi.fn() });

        const close = screen.getByRole('button', { name: 'Close' });
        const continueButton = screen.getByRole('button', {
            name: 'Apply Corrections & Continue'
        });
        const finishButton = screen.getByRole('button', {
            name: 'Apply Corrections & Finish'
        });

        expect(
            close.compareDocumentPosition(continueButton) & Node.DOCUMENT_POSITION_FOLLOWING
        ).toBeTruthy();
        expect(
            continueButton.compareDocumentPosition(finishButton) & Node.DOCUMENT_POSITION_FOLLOWING
        ).toBeTruthy();
        expect(continueButton).toHaveClass('bg-secondary');
        expect(finishButton).toHaveClass('bg-primary');
    });

    it('does not record agreement when refinement fails', async () => {
        mocks.refineClassifier.mockRejectedValue(new Error('Training failed'));
        render(RefineClassifierDialog, { onCancel: vi.fn(), onFinish: vi.fn() });

        await fireEvent.click(screen.getByRole('button', { name: 'Apply Corrections & Continue' }));

        await waitFor(() => expect(screen.getByText('Training failed')).toBeInTheDocument());
        expect(get(classifierWorkflow.workflow).reviewedSamples).toBe(0);
    });

    it('shows distinct latest-round and weighted overall agreement', async () => {
        classifierWorkflow.recordReview(4, 4);
        render(RefineClassifierDialog, { onCancel: vi.fn(), onFinish: vi.fn() });

        await fireEvent.click(screen.getByRole('button', { name: 'Apply Corrections & Continue' }));

        await waitFor(() => {
            expect(screen.getByText(/Overall review agreement: 75%/)).toBeInTheDocument();
            expect(screen.getByText(/Latest-round agreement: 50%/)).toBeInTheDocument();
            expect(screen.getByText(/6 of 8 predictions confirmed/)).toBeInTheDocument();
        });
    });

    it('excludes training-history submissions from agreement', async () => {
        render(RefineClassifierDialog, { onCancel: vi.fn(), onFinish: vi.fn() });

        await fireEvent.click(screen.getByRole('switch'));
        await waitFor(() => expect(mocks.showClassifierTrainingSamples).toHaveBeenCalled());
        await fireEvent.click(screen.getByRole('button', { name: 'Apply Corrections & Continue' }));

        await waitFor(() => expect(mocks.refineClassifier).toHaveBeenCalled());
        expect(get(classifierWorkflow.workflow).reviewedSamples).toBe(0);
    });

    it('applies current corrections before saving and finishing', async () => {
        classifierWorkflow.openRefine('temp', 'classifier-id', 'Zebras', ['positive', 'negative']);
        const onFinish = vi.fn();
        render(RefineClassifierDialog, { onCancel: vi.fn(), onFinish });

        await fireEvent.click(screen.getByRole('button', { name: 'Save Classifier & Finish' }));

        await waitFor(() => expect(onFinish).toHaveBeenCalledOnce());
        expect(mocks.applyClassifierCorrections).toHaveBeenCalledWith('classifier-id');
        expect(mocks.commitTempClassifier).toHaveBeenCalledWith('classifier-id', 'collection-id');
        expect(mocks.applyClassifierCorrections.mock.invocationCallOrder[0]).toBeLessThan(
            mocks.commitTempClassifier.mock.invocationCallOrder[0]
        );
    });

    it('stays open when applying corrections before finish fails', async () => {
        mocks.applyClassifierCorrections.mockRejectedValue(new Error('Training failed'));
        const onFinish = vi.fn();
        render(RefineClassifierDialog, { onCancel: vi.fn(), onFinish });

        await fireEvent.click(screen.getByRole('button', { name: 'Apply Corrections & Finish' }));

        await waitFor(() => expect(screen.getByText('Training failed')).toBeInTheDocument());
        expect(onFinish).not.toHaveBeenCalled();
        expect(mocks.commitTempClassifier).not.toHaveBeenCalled();
    });

    it('stays open when committing after corrections fails', async () => {
        classifierWorkflow.openRefine('temp', 'classifier-id', 'Zebras', ['positive', 'negative']);
        mocks.commitTempClassifier.mockRejectedValue(new Error('Commit failed'));
        const onFinish = vi.fn();
        render(RefineClassifierDialog, { onCancel: vi.fn(), onFinish });

        await fireEvent.click(screen.getByRole('button', { name: 'Save Classifier & Finish' }));

        await waitFor(() => expect(screen.getByText('Commit failed')).toBeInTheDocument());
        expect(mocks.applyClassifierCorrections).toHaveBeenCalledOnce();
        expect(onFinish).not.toHaveBeenCalled();
    });
});
