import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useClassifierState } from '$lib/hooks/useClassifiers/useClassifierState';
import CreateClassifierDialog from './CreateClassifierDialog.svelte';

const mocks = vi.hoisted(() => ({
    createClassifier: vi.fn()
}));

vi.mock('$app/state', () => ({
    page: { params: { collection_id: 'collection-id' } }
}));

vi.mock('$lib/hooks/useClassifiers/useClassifiers', () => ({
    useClassifiers: () => ({ createClassifier: mocks.createClassifier })
}));

vi.mock('$lib/hooks/useImagesInfinite/useImagesInfinite', () => ({
    useImagesInfinite: () => ({
        samples: {
            isPending: false,
            isError: false,
            isSuccess: true,
            data: { pages: [{ data: [] }] }
        }
    })
}));

const classifierState = useClassifierState();

describe('CreateClassifierDialog', () => {
    beforeEach(() => {
        mocks.createClassifier.mockReset().mockResolvedValue({});
        classifierState.clearClassifierSelectedSamples();
    });

    afterEach(() => {
        classifierState.clearClassifierSelectedSamples();
    });

    it('explains the workflow and requires a name and matching example', async () => {
        render(CreateClassifierDialog, { onCancel: vi.fn() });

        expect(screen.getByText(/do not need to select every matching image/i)).toBeInTheDocument();

        const submitButton = screen.getByRole('button', { name: 'Train Classifier' });
        const nameInput = screen.getByPlaceholderText('For example, zebras or damaged products');
        await fireEvent.input(nameInput, { target: { value: 'Zebras' } });
        expect(submitButton).toBeDisabled();

        classifierState.classifierSelectedSampleIds.set(new Set(['sample-1']));

        await waitFor(() => expect(submitButton).toBeEnabled());
        expect(screen.getByText(/1 selected ·/)).toBeInTheDocument();
    });

    it('trains with the fixed binary classes after the form is complete', async () => {
        classifierState.classifierSelectedSampleIds.set(new Set(['sample-1']));
        render(CreateClassifierDialog, { onCancel: vi.fn() });

        await fireEvent.input(
            screen.getByPlaceholderText('For example, zebras or damaged products'),
            { target: { value: 'Zebras' } }
        );
        await fireEvent.click(screen.getByRole('button', { name: 'Train Classifier' }));

        await waitFor(() => {
            expect(mocks.createClassifier).toHaveBeenCalledWith({
                name: 'Zebras',
                class_list: ['positive', 'negative'],
                collection_id: 'collection-id'
            });
        });
    });
});
