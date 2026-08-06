import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useClassesDialog } from '$lib/hooks/useClassesDialog/useClassesDialog';
import { useClasses } from '$lib/hooks/useClasses/useClasses.svelte';
import ClassesDialog from './ClassesDialog.svelte';

vi.mock('$lib/hooks/useClasses/useClasses.svelte', () => ({ useClasses: vi.fn() }));

const cat = {
    annotation_label_id: 'cat-id',
    dataset_id: 'dataset-id',
    annotation_label_name: 'cat',
    created_at: '2026-01-01',
    annotation_count: 3
};
const addClasses = vi.fn();
const { openClassesDialog, closeClassesDialog } = useClassesDialog();

function renderDialog(labels = [cat]) {
    vi.mocked(useClasses).mockReturnValue({
        query: { data: labels, isPending: false, isError: false },
        addClasses
    } as unknown as ReturnType<typeof useClasses>);
    render(ClassesDialog, { props: { collectionId: 'collection-id' } });
    openClassesDialog();
}

describe('ClassesDialog', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        addClasses.mockResolvedValue(undefined);
        closeClassesDialog();
    });

    afterEach(() => {
        closeClassesDialog();
        document.body.innerHTML = '';
    });

    it('adds normalized comma-separated class names and renders counts', async () => {
        const user = userEvent.setup();
        renderDialog();

        expect(await screen.findByText('cat')).toBeInTheDocument();
        expect(screen.getByText('3')).toBeInTheDocument();
        await user.type(screen.getByLabelText('Class names'), ' dog, , bird, dog ');
        await user.click(screen.getByRole('button', { name: 'Add' }));

        await waitFor(() => expect(addClasses).toHaveBeenCalledWith(['dog', 'bird']));
    });

    it('filters existing classes before adding and reports them', async () => {
        const user = userEvent.setup();
        renderDialog();
        await screen.findByText('cat');

        await user.type(screen.getByLabelText('Class names'), 'CAT, dog');
        await user.click(screen.getByRole('button', { name: 'Add' }));

        await waitFor(() => expect(addClasses).toHaveBeenCalledWith(['dog']));
        expect(screen.getByRole('status')).toHaveTextContent('Already exist: CAT.');
    });

    it('does not submit when every class already exists', async () => {
        const user = userEvent.setup();
        renderDialog();
        await screen.findByText('cat');

        await user.type(screen.getByLabelText('Class names'), 'cat');
        await user.click(screen.getByRole('button', { name: 'Add' }));

        expect(addClasses).not.toHaveBeenCalled();
        expect(screen.getByRole('status')).toHaveTextContent('All classes already exist.');
    });
});
