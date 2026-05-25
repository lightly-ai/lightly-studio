import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import AddStrategyButton from './AddStrategyButton.svelte';

describe('AddStrategyButton', () => {
    it('shows the strategy menu when the trigger is clicked', async () => {
        render(AddStrategyButton, {
            props: {
                onAdd: vi.fn()
            }
        });

        await fireEvent.click(screen.getByTestId('add-strategy-button'));

        expect(await screen.findByTestId('add-strategy-diversity')).toBeInTheDocument();
    });

    it('calls onAdd with the selected strategy type', async () => {
        const onAdd = vi.fn();

        render(AddStrategyButton, {
            props: { onAdd }
        });

        await fireEvent.click(screen.getByTestId('add-strategy-button'));
        await fireEvent.click(await screen.findByTestId('add-strategy-metadata_weighting'));

        expect(onAdd).toHaveBeenCalledWith('metadata_weighting');
    });

    it('disables the similarity option when requested', async () => {
        render(AddStrategyButton, {
            props: {
                isSimilarityDisabled: true,
                onAdd: vi.fn()
            }
        });

        await fireEvent.click(screen.getByTestId('add-strategy-button'));

        expect(await screen.findByTestId('add-strategy-similarity')).toBeDisabled();
    });
});
