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
        expect(onSubmit).toHaveBeenLastCalledWith({ splits, seed: 42 });
        await fireEvent.input(screen.getByLabelText('Seed (optional)'), { target: { value: '' } });
        await fireEvent.click(button);
        expect(onSubmit).toHaveBeenLastCalledWith({ splits });
        await fireEvent.input(screen.getByLabelText('Seed (optional)'), {
            target: { value: '-7' }
        });
        await fireEvent.click(button);
        expect(onSubmit).toHaveBeenLastCalledWith({ splits, seed: -7 });
    });

    it('adds five splits, validates new names and submits their weights', async () => {
        const onSubmit = vi.fn();
        render(DatasetSplitDialog, { ...defaultProps, sampleCount: 5, onSubmit });
        const add = screen.getByRole('button', { name: 'Add split' });
        for (const index of [4, 5]) {
            await fireEvent.click(add);
            expect(screen.getByRole('button', { name: 'Split dataset' })).toBeDisabled();
            await fireEvent.input(screen.getByLabelText(`Tag ${index}`), {
                target: { value: `chunk-${index}` }
            });
        }
        expect(add).toBeDisabled();
        expect(screen.getByLabelText('Split 1 sample count')).toHaveTextContent('3 samples');
        await fireEvent.click(screen.getByRole('button', { name: 'Split dataset' }));
        expect(onSubmit).toHaveBeenCalledWith({
            splits: ['train', 'val', 'test', 'chunk-4', 'chunk-5'].map((tag_name, index) => ({
                tag_name,
                relative_size: index === 0 ? 8 : 1
            })),
            seed: 42
        });
    });

    it('removes a middle split while preserving remaining values and requires two splits', async () => {
        render(DatasetSplitDialog, defaultProps);
        await fireEvent.click(screen.getByRole('button', { name: 'Remove split 2' }));
        expect(screen.getByLabelText('Tag 2')).toHaveValue('test');
        expect(screen.getByLabelText('Split 1 sample count')).toHaveTextContent('10 samples');
        expect(screen.getByLabelText('Split 2 sample count')).toHaveTextContent('1 sample');
        expect(screen.getAllByRole('button', { name: /Remove split/ })).toHaveLength(2);
        for (const button of screen.getAllByRole('button', { name: /Remove split/ })) {
            expect(button).toBeDisabled();
        }
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
        expect(screen.getByRole('button', { name: 'Add split' })).toBeDisabled();
        expect(screen.getByRole('button', { name: 'Remove split 1' })).toBeDisabled();
        await fireEvent.submit(button.closest('form')!);
        expect(onSubmit).not.toHaveBeenCalled();
        await rerender({ pending: false, error: 'Unable to split dataset.' });
        expect(screen.getByRole('alert')).toHaveTextContent('Unable to split dataset.');
        expect(screen.getByLabelText('Tag 1')).toHaveValue('training');
        await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
        expect(onClose).toHaveBeenCalledOnce();
    });
});
