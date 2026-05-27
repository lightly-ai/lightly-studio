import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import StrategySelect from './StrategySelect.svelte';

describe('StrategySelect', () => {
    beforeEach(() => {
        Element.prototype.scrollIntoView = vi.fn();
    });

    it('shows "Select strategy" when no strategy is selected', () => {
        render(StrategySelect, {
            props: { value: '', isSimilaritySupported: true, onValueChange: vi.fn() }
        });

        expect(screen.getByTestId('selection-dialog-strategy-select')).toHaveTextContent(
            'Select strategy'
        );
    });

    it('shows the label of the currently selected strategy', () => {
        render(StrategySelect, {
            props: { value: 'diversity', isSimilaritySupported: true, onValueChange: vi.fn() }
        });

        expect(screen.getByTestId('selection-dialog-strategy-select')).toHaveTextContent(
            'Diversity'
        );
    });

    it('calls onValueChange with the selected strategy value', async () => {
        const onValueChange = vi.fn();
        render(StrategySelect, {
            props: { value: '', isSimilaritySupported: true, onValueChange }
        });

        await fireEvent.keyDown(screen.getByTestId('selection-dialog-strategy-select'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(await screen.findByTestId('selection-strategy-typicality'));

        expect(onValueChange).toHaveBeenCalledWith('typicality');
    });

    it('disables the similarity option when isSimilaritySupported is false', async () => {
        render(StrategySelect, {
            props: { value: '', isSimilaritySupported: false, onValueChange: vi.fn() }
        });

        await fireEvent.keyDown(screen.getByTestId('selection-dialog-strategy-select'), {
            key: 'Enter'
        });

        expect(await screen.findByTestId('selection-strategy-similarity')).toHaveAttribute(
            'data-disabled'
        );
    });

    it('enables the similarity option when isSimilaritySupported is true', async () => {
        render(StrategySelect, {
            props: { value: '', isSimilaritySupported: true, onValueChange: vi.fn() }
        });

        await fireEvent.keyDown(screen.getByTestId('selection-dialog-strategy-select'), {
            key: 'Enter'
        });

        expect(await screen.findByTestId('selection-strategy-similarity')).not.toHaveAttribute(
            'data-disabled'
        );
    });
});
