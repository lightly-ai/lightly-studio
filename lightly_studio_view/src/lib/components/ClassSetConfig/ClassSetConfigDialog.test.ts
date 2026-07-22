import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ClassSetConfigDialog from './ClassSetConfigDialog.svelte';
import type { ClassSetSelection } from './types';

type Sort = 'count' | 'name';

const baseSelection: ClassSetSelection<Sort> = {
    mode: 'topN',
    n: 5,
    sortBy: 'count',
    manualClasses: []
};

const sortItems = [
    { value: 'count', label: 'Count' },
    { value: 'name', label: 'Class name' }
];

const allClasses = Array.from({ length: 30 }, (_, i) => `class-${i}`);

const renderDialog = (overrides: Partial<Parameters<typeof render>[1]> = {}) => {
    const onApply = vi.fn();
    render(ClassSetConfigDialog, {
        props: {
            open: true,
            allClasses,
            selection: baseSelection,
            sortItems,
            description: 'Choose which classes the chart shows.',
            testIdPrefix: 'cfg',
            onApply,
            ...overrides
        }
    });
    return { onApply };
};

describe('ClassSetConfigDialog', () => {
    afterEach(() => {
        // bits-ui dialogs portal into the body and can leave styles behind.
        document.body.innerHTML = '';
        document.body.style.pointerEvents = '';
    });

    it('renders the title, description and seeds the input from the selection', () => {
        renderDialog();

        expect(screen.getByText('Configure classes')).toBeInTheDocument();
        expect(screen.getByText('Choose which classes the chart shows.')).toBeInTheDocument();
        const input = screen.getByTestId('cfg-top-n');
        expect(input).toHaveValue(5);
        expect(input).toHaveAttribute('min', '1');
        expect(input).toHaveAttribute('max', '30');
    });

    it('shows the label of the current sort option on the trigger', () => {
        renderDialog({ selection: { ...baseSelection, sortBy: 'name' } });

        expect(screen.getByTestId('cfg-sort-by')).toHaveTextContent('Class name');
    });

    it('applies the edited top-N and closes', async () => {
        const { onApply } = renderDialog();

        await fireEvent.input(screen.getByTestId('cfg-top-n'), { target: { value: '8' } });
        await fireEvent.click(screen.getByTestId('cfg-apply'));

        expect(onApply).toHaveBeenCalledWith({ ...baseSelection, n: 8 });
        await waitFor(() =>
            expect(screen.queryByText('Configure classes')).not.toBeInTheDocument()
        );
    });

    it('clamps top-N above the class count back down on apply', async () => {
        const { onApply } = renderDialog();

        await fireEvent.input(screen.getByTestId('cfg-top-n'), { target: { value: '999' } });
        await fireEvent.click(screen.getByTestId('cfg-apply'));

        expect(onApply).toHaveBeenCalledWith({ ...baseSelection, n: 30 });
    });

    it('falls back to 1 when the input is cleared to a non-finite value', async () => {
        const { onApply } = renderDialog();

        await fireEvent.input(screen.getByTestId('cfg-top-n'), { target: { value: '' } });
        await fireEvent.click(screen.getByTestId('cfg-apply'));

        expect(onApply).toHaveBeenCalledWith({ ...baseSelection, n: 1 });
    });

    it('hides the "All" quick action unless showAllButton is set', () => {
        renderDialog();

        expect(screen.queryByTestId('cfg-all')).not.toBeInTheDocument();
    });

    it('sets top-N to the class count via the "All" quick action', async () => {
        const { onApply } = renderDialog({ showAllButton: true });

        await fireEvent.click(screen.getByTestId('cfg-all'));
        await fireEvent.click(screen.getByTestId('cfg-apply'));

        expect(onApply).toHaveBeenCalledWith({ ...baseSelection, n: 30 });
    });

    it('applies the manually selected classes', async () => {
        const { onApply } = renderDialog({
            selection: { ...baseSelection, mode: 'manual', manualClasses: ['class-2'] }
        });

        await fireEvent.click(screen.getByTestId('cfg-apply'));

        expect(onApply).toHaveBeenCalledWith(
            expect.objectContaining({ mode: 'manual', manualClasses: ['class-2'] })
        );
    });

    it('disables Apply in manual mode when no class is selected', async () => {
        renderDialog({ selection: { ...baseSelection, mode: 'manual', manualClasses: [] } });

        await waitFor(() => expect(screen.getByTestId('cfg-apply')).toBeDisabled());
    });

    it('closes without applying when Cancel is clicked', async () => {
        const { onApply } = renderDialog();

        await fireEvent.click(screen.getByText('Cancel'));

        expect(onApply).not.toHaveBeenCalled();
    });
});
