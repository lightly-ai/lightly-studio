import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import CuboidSourceSection from './CuboidSourceSection.svelte';

const defaultProps = { sourceNames: ['labels', 'preds'], selected: null, onSelect: vi.fn() };

describe('CuboidSourceSection', () => {
    it('lists the sources and checks the selected one', () => {
        render(CuboidSourceSection, {
            props: { ...defaultProps, selected: { name: 'preds', isNew: false } }
        });

        expect(screen.getByTestId('annotation-target-radio-preds')).toHaveAttribute(
            'aria-checked',
            'true'
        );
        expect(screen.getByTestId('annotation-target-radio-labels')).toHaveAttribute(
            'aria-checked',
            'false'
        );
    });

    it('selects a clicked source', async () => {
        const onSelect = vi.fn();
        render(CuboidSourceSection, { props: { ...defaultProps, onSelect } });

        await fireEvent.click(screen.getByTestId('annotation-target-radio-labels'));

        expect(onSelect).toHaveBeenCalledWith({ name: 'labels', isNew: false });
    });

    it('selects a typed name as a new source', async () => {
        const onSelect = vi.fn();
        render(CuboidSourceSection, { props: { ...defaultProps, onSelect } });

        await fireEvent.click(screen.getByTestId('new-annotation-source-button'));
        const input = screen.getByTestId('new-annotation-source-input');
        await fireEvent.input(input, { target: { value: 'review' } });
        await fireEvent.submit(input.closest('form')!);

        expect(onSelect).toHaveBeenCalledWith({ name: 'review', isNew: true });
    });

    it('shows a selected new source as checked', () => {
        render(CuboidSourceSection, {
            props: { ...defaultProps, selected: { name: 'review', isNew: true } }
        });

        expect(screen.getByTestId('annotation-target-radio-review')).toHaveAttribute(
            'aria-checked',
            'true'
        );
    });
});
