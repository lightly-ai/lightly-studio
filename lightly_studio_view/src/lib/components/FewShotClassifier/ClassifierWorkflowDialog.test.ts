import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { get } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useClassifierWorkflow } from '$lib/hooks/useClassifiers/useClassifierWorkflow';
import ClassifierWorkflowDialog from './ClassifierWorkflowDialog.svelte';

const mocks = vi.hoisted(() => ({
    dropTempClassifier: vi.fn()
}));

vi.mock('$app/state', () => ({
    page: { params: { collection_id: 'collection-id' } }
}));

vi.mock('$lib/hooks/useClassifiers/useClassifiers', () => ({
    useClassifiers: () => ({ dropTempClassifier: mocks.dropTempClassifier })
}));

vi.mock('./CreateClassifierDialog.svelte', () => ({ default: vi.fn() }));
vi.mock('./RefineClassifierDialog.svelte', () => ({ default: vi.fn() }));

describe('ClassifierWorkflowDialog', () => {
    const classifierWorkflow = useClassifierWorkflow();

    beforeEach(() => {
        vi.resetAllMocks();
        mocks.dropTempClassifier.mockResolvedValue(undefined);
        classifierWorkflow.close();
    });

    it('shows the complete process from the creation phase', () => {
        classifierWorkflow.openCreate();
        render(ClassifierWorkflowDialog);

        expect(screen.getByText('1. Choose examples')).toBeInTheDocument();
        expect(screen.getByText('2. Review predictions')).toBeInTheDocument();
        expect(screen.getByText('Repeat as useful')).toBeInTheDocument();
        expect(screen.getByText('3. Finish')).toBeInTheDocument();
        expect(screen.getByText('Save classifier')).toBeInTheDocument();
    });

    it('collapses guidance when creation transitions to refinement', async () => {
        classifierWorkflow.openCreate();
        render(ClassifierWorkflowDialog);

        classifierWorkflow.openRefine('temp', 'temporary-id', 'Zebras', ['positive', 'negative']);

        const trigger = await screen.findByRole('button', {
            name: /Step 2 of 3: Review predictions/i
        });
        await waitFor(() =>
            expect(screen.getByText('Checked images are predicted matches.')).not.toBeVisible()
        );

        await fireEvent.click(trigger);
        expect(screen.getByText('Checked images are predicted matches.')).toBeInTheDocument();
    });

    it('drops a temporary classifier when the workflow is cancelled', async () => {
        classifierWorkflow.openRefine('temp', 'temporary-id', 'Zebras', ['positive', 'negative']);
        render(ClassifierWorkflowDialog);

        await fireEvent.click(screen.getByRole('button', { name: 'Close' }));

        await waitFor(() => {
            expect(mocks.dropTempClassifier).toHaveBeenCalledWith('temporary-id');
            expect(get(classifierWorkflow.workflow).phase).toBe('closed');
        });
    });

    it('preserves an existing classifier when the workflow closes', async () => {
        classifierWorkflow.openRefine('existing', 'existing-id', 'Zebras', [
            'positive',
            'negative'
        ]);
        render(ClassifierWorkflowDialog);

        await fireEvent.click(screen.getByRole('button', { name: 'Close' }));

        await waitFor(() => expect(get(classifierWorkflow.workflow).phase).toBe('closed'));
        expect(mocks.dropTempClassifier).not.toHaveBeenCalled();
    });
});
