import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import BulkClassificationPanel from './BulkClassificationPanel.svelte';

const defaultProps = {
    selectedCount: 10,
    sourceName: 'ground_truth',
    className: 'dog',
    sourceNames: ['ground_truth'],
    classNames: ['dog'],
    onSourceSelect: vi.fn(),
    onClassSelect: vi.fn(),
    onApply: vi.fn()
};

describe('BulkClassificationPanel', () => {
    it('renders the approved panel copy', () => {
        render(BulkClassificationPanel, { props: defaultProps });

        expect(screen.getByText('Selected images: 10')).toBeInTheDocument();
        expect(screen.getByText('Annotation source')).toBeInTheDocument();
        expect(screen.getByText('Annotation class')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Add annotation class/ })).toBeInTheDocument();
    });

    it('labels each picker independently of the selected value', () => {
        render(BulkClassificationPanel, { props: defaultProps });

        expect(screen.getByRole('combobox', { name: /^Annotation source/ })).toBeInTheDocument();
        expect(screen.getByRole('combobox', { name: /^Annotation class/ })).toBeInTheDocument();
    });

    it('confirms before applying', async () => {
        const onApply = vi.fn();
        render(BulkClassificationPanel, { props: { ...defaultProps, onApply } });

        await fireEvent.click(screen.getByRole('button', { name: /Add annotation class/ }));

        expect(onApply).not.toHaveBeenCalled();
        expect(screen.getByRole('heading', { name: 'Add annotation class' })).toBeInTheDocument();
        expect(screen.getAllByText('dog')).toHaveLength(2);
        expect(screen.getAllByText('ground_truth')).toHaveLength(2);

        await fireEvent.click(
            screen.getAllByRole('button', { name: /Add annotation class/ }).at(-1)!
        );

        expect(onApply).toHaveBeenCalledOnce();
    });

    it('closes the confirmation when applying fails', async () => {
        const onApply = vi.fn().mockRejectedValue(new Error('failed'));
        render(BulkClassificationPanel, { props: { ...defaultProps, onApply } });

        await fireEvent.click(screen.getByRole('button', { name: /Add annotation class/ }));
        await fireEvent.click(
            screen.getAllByRole('button', { name: /Add annotation class/ }).at(-1)!
        );

        expect(onApply).toHaveBeenCalledOnce();
        expect(screen.queryByRole('heading', { name: 'Add annotation class' })).toBeNull();
    });

    it('applies once when the confirmation is clicked twice', async () => {
        let resolveApply = () => {};
        const onApply = vi.fn().mockReturnValue(
            new Promise<void>((resolve) => {
                resolveApply = resolve;
            })
        );
        render(BulkClassificationPanel, { props: { ...defaultProps, onApply } });

        await fireEvent.click(screen.getByRole('button', { name: /Add annotation class/ }));
        const confirm = screen.getAllByRole('button', { name: /Add annotation class/ }).at(-1)!;
        await fireEvent.click(confirm);
        await fireEvent.click(confirm);

        expect(onApply).toHaveBeenCalledOnce();

        resolveApply();
    });

    it('disables applying while in flight', () => {
        render(BulkClassificationPanel, { props: { ...defaultProps, isApplying: true } });

        expect(screen.getByRole('button', { name: /Add annotation class/ })).toBeDisabled();
    });

    it('disables applying without a selection', () => {
        render(BulkClassificationPanel, { props: { ...defaultProps, selectedCount: 0 } });

        expect(screen.getByRole('button', { name: /Add annotation class/ })).toBeDisabled();
    });
});
