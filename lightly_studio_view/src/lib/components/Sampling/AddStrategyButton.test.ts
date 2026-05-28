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

    it('closes the popover after selecting a strategy', async () => {
        const onAdd = vi.fn();

        render(AddStrategyButton, {
            props: { onAdd }
        });

        await fireEvent.click(screen.getByTestId('add-strategy-button'));
        await fireEvent.click(await screen.findByTestId('add-strategy-diversity'));

        expect(screen.queryByTestId('add-strategy-typicality')).not.toBeInTheDocument();
    });

    it('disables the similarity option when a reason is provided', async () => {
        render(AddStrategyButton, {
            props: {
                similarityDisabledReason: 'No query tag selected',
                onAdd: vi.fn()
            }
        });

        await fireEvent.click(screen.getByTestId('add-strategy-button'));

        expect(await screen.findByTestId('add-strategy-similarity')).toBeDisabled();
    });

    it('disables the metadata weighting option when a reason is provided', async () => {
        render(AddStrategyButton, {
            props: {
                metadataWeightingDisabledReason: 'No numeric metadata available',
                onAdd: vi.fn()
            }
        });

        await fireEvent.click(screen.getByTestId('add-strategy-button'));

        expect(await screen.findByTestId('add-strategy-metadata_weighting')).toBeDisabled();
    });

    it('disables the class balancing option when a reason is provided', async () => {
        render(AddStrategyButton, {
            props: {
                classBalancingDisabledReason: 'No annotations available',
                onAdd: vi.fn()
            }
        });

        await fireEvent.click(screen.getByTestId('add-strategy-button'));

        expect(await screen.findByTestId('add-strategy-class_balancing')).toBeDisabled();
    });

    it('shows a tooltip with the strategy description on hover', async () => {
        render(AddStrategyButton, {
            props: { onAdd: vi.fn() }
        });

        await fireEvent.click(screen.getByTestId('add-strategy-button'));
        const button = await screen.findByTestId('add-strategy-diversity');
        await fireEvent.mouseEnter(button.parentElement!);

        expect(screen.getByRole('tooltip')).toBeInTheDocument();
    });

    it('shows the disabled reason in the tooltip on hover', async () => {
        render(AddStrategyButton, {
            props: {
                similarityDisabledReason: 'No query tag selected',
                onAdd: vi.fn()
            }
        });

        await fireEvent.click(screen.getByTestId('add-strategy-button'));
        const button = await screen.findByTestId('add-strategy-similarity');
        await fireEvent.mouseEnter(button.parentElement!);

        expect(screen.getByRole('tooltip')).toHaveTextContent('No query tag selected');
    });
});
