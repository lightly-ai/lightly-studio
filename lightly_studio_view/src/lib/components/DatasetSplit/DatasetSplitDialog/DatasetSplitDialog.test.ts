import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import DatasetSplitDialog from './DatasetSplitDialog.svelte';

const defaultProps = {
    sampleCount: 11,
    existingTagNames: [],
    onSubmit: vi.fn(),
    onClose: vi.fn()
};

describe('DatasetSplitDialog', () => {
    it('updates counts and submits trimmed names with an optional seed', async () => {
        const onSubmit = vi.fn();
        render(DatasetSplitDialog, { ...defaultProps, onSubmit });
        expect(screen.getByLabelText('Split 1 sample count')).toHaveTextContent('9 samples');
        await fireEvent.input(screen.getByLabelText('Tag 1'), { target: { value: ' training ' } });
        await fireEvent.input(screen.getByLabelText('Weight 1'), { target: { value: '1' } });
        expect(screen.getByLabelText('Split 1 sample count')).toHaveTextContent('4 samples');
        expect(screen.getByLabelText('Split 2 sample count')).toHaveTextContent('4 samples');
        expect(screen.getByLabelText('Split 3 sample count')).toHaveTextContent('3 samples');
        const button = screen.getByRole('button', { name: 'Split dataset' });
        await fireEvent.click(button);
        const splits = ['training', 'val', 'test'].map((tag_name) => ({
            tag_name,
            relative_size: 1
        }));
        expect(onSubmit).toHaveBeenLastCalledWith({ splits });
        await fireEvent.input(screen.getByLabelText('Seed (optional)'), {
            target: { value: '-7' }
        });
        await fireEvent.click(button);
        expect(onSubmit).toHaveBeenLastCalledWith({ splits, seed: -7 });
    });

    it.each([
        ['Tag 1', 'val', 'different name'],
        ['Tag 1', 'existing', 'already exists'],
        ['Weight 1', '', 'positive whole numbers'],
        ['Seed (optional)', '1.5', 'Seed must be a whole number'],
        ['Seed (optional)', 'invalid', 'Seed must be a whole number']
    ])('blocks invalid input in %s: %s', async (label, value, message) => {
        const onSubmit = vi.fn();
        render(DatasetSplitDialog, { ...defaultProps, existingTagNames: ['existing'], onSubmit });
        await fireEvent.input(screen.getByLabelText(label), { target: { value } });
        expect(screen.getByRole('alert')).toHaveTextContent(message);
        expect(screen.getByRole('button', { name: 'Split dataset' })).toBeDisabled();
        await fireEvent.submit(
            screen.getByRole('button', { name: 'Split dataset' }).closest('form')!
        );
        expect(onSubmit).not.toHaveBeenCalled();
    });

    it('blocks pending submissions and preserves values after an error', async () => {
        const onSubmit = vi.fn();
        const onClose = vi.fn();
        const { rerender } = render(DatasetSplitDialog, { ...defaultProps, onSubmit, onClose });
        await fireEvent.input(screen.getByLabelText('Tag 1'), { target: { value: 'training' } });
        await rerender({ pending: true });
        const button = screen.getByRole('button', { name: 'Splitting…' });
        expect(button).toBeDisabled();
        await fireEvent.submit(button.closest('form')!);
        expect(onSubmit).not.toHaveBeenCalled();
        await rerender({ pending: false, error: 'Unable to split dataset.' });
        expect(screen.getByRole('alert')).toHaveTextContent('Unable to split dataset.');
        expect(screen.getByLabelText('Tag 1')).toHaveValue('training');
        await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
        expect(onClose).toHaveBeenCalledOnce();
    });
});
