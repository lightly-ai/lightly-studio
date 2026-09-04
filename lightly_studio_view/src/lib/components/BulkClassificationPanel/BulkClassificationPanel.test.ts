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

        expect(screen.getByText('10 images selected')).toBeInTheDocument();
        expect(screen.getByText('Source')).toBeInTheDocument();
        expect(screen.getByText('Class')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Add class' })).toBeInTheDocument();
        expect(
            screen.getByText('Change or remove annotations in the annotation view.')
        ).toBeInTheDocument();
    });

    it('confirms before applying', async () => {
        const onApply = vi.fn();
        render(BulkClassificationPanel, { props: { ...defaultProps, onApply } });

        await fireEvent.click(screen.getByRole('button', { name: 'Add class' }));

        expect(onApply).not.toHaveBeenCalled();
        expect(screen.getByRole('heading', { name: 'Add class' })).toBeInTheDocument();
        expect(screen.getAllByText('dog')).toHaveLength(2);
        expect(screen.getAllByText('ground_truth')).toHaveLength(2);

        await fireEvent.click(screen.getAllByRole('button', { name: 'Add class' }).at(-1)!);

        expect(onApply).toHaveBeenCalledOnce();
    });

    it('disables applying while in flight', () => {
        render(BulkClassificationPanel, { props: { ...defaultProps, isApplying: true } });

        expect(screen.getByRole('button', { name: 'Add class' })).toBeDisabled();
    });
});
