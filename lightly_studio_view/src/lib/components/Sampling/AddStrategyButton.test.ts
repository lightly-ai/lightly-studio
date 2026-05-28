import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AddStrategyButton from './AddStrategyButton.svelte';

describe('AddStrategyButton', () => {
    beforeEach(() => {
        Element.prototype.scrollIntoView = vi.fn();
    });

    it('shows the strategy menu when the trigger is clicked', async () => {
        render(AddStrategyButton, {
            props: {
                onAdd: vi.fn()
            }
        });

        await fireEvent.keyDown(screen.getByTestId('add-strategy-button'), { key: 'Enter' });

        expect(await screen.findByTestId('add-strategy-diversity')).toBeInTheDocument();
    });

    it('calls onAdd with the selected strategy type', async () => {
        const onAdd = vi.fn();

        render(AddStrategyButton, {
            props: { onAdd }
        });

        await fireEvent.keyDown(screen.getByTestId('add-strategy-button'), { key: 'Enter' });
        await fireEvent.pointerUp(await screen.findByTestId('add-strategy-metadata_weighting'));

        expect(onAdd).toHaveBeenCalledWith('metadata_weighting');
    });

    it('closes the select after selecting a strategy', async () => {
        const onAdd = vi.fn();

        render(AddStrategyButton, {
            props: { onAdd }
        });

        await fireEvent.keyDown(screen.getByTestId('add-strategy-button'), { key: 'Enter' });
        await fireEvent.pointerUp(await screen.findByTestId('add-strategy-diversity'));

        expect(screen.queryByTestId('add-strategy-typicality')).not.toBeInTheDocument();
    });

    it('disables the similarity option when a reason is provided', async () => {
        render(AddStrategyButton, {
            props: {
                similarityDisabledReason: 'No query tag selected',
                onAdd: vi.fn()
            }
        });

        await fireEvent.keyDown(screen.getByTestId('add-strategy-button'), { key: 'Enter' });

        expect(await screen.findByTestId('add-strategy-similarity')).toHaveAttribute(
            'data-disabled'
        );
    });

    it('disables the metadata weighting option when a reason is provided', async () => {
        render(AddStrategyButton, {
            props: {
                metadataWeightingDisabledReason: 'No numeric metadata available',
                onAdd: vi.fn()
            }
        });

        await fireEvent.keyDown(screen.getByTestId('add-strategy-button'), { key: 'Enter' });

        expect(await screen.findByTestId('add-strategy-metadata_weighting')).toHaveAttribute(
            'data-disabled'
        );
    });

    it('disables the class balancing option when a reason is provided', async () => {
        render(AddStrategyButton, {
            props: {
                classBalancingDisabledReason: 'No annotations available',
                onAdd: vi.fn()
            }
        });

        await fireEvent.keyDown(screen.getByTestId('add-strategy-button'), { key: 'Enter' });

        expect(await screen.findByTestId('add-strategy-class_balancing')).toHaveAttribute(
            'data-disabled'
        );
    });

    it('does not call onAdd when a disabled option is clicked', async () => {
        const onAdd = vi.fn();

        render(AddStrategyButton, {
            props: {
                similarityDisabledReason: 'No query tag selected',
                onAdd
            }
        });

        await fireEvent.keyDown(screen.getByTestId('add-strategy-button'), { key: 'Enter' });
        await fireEvent.pointerUp(await screen.findByTestId('add-strategy-similarity'));

        expect(onAdd).not.toHaveBeenCalled();
    });

    it('shows a tooltip with the strategy description on hover', async () => {
        render(AddStrategyButton, {
            props: { onAdd: vi.fn() }
        });

        await fireEvent.keyDown(screen.getByTestId('add-strategy-button'), { key: 'Enter' });
        const button = await screen.findByTestId('add-strategy-diversity');
        await fireEvent.mouseEnter(button.parentElement!);

        expect(await screen.findByRole('tooltip')).toBeInTheDocument();
    });

    it('shows the disabled reason in the tooltip on hover', async () => {
        render(AddStrategyButton, {
            props: {
                similarityDisabledReason: 'No query tag selected',
                onAdd: vi.fn()
            }
        });

        await fireEvent.keyDown(screen.getByTestId('add-strategy-button'), { key: 'Enter' });
        const button = await screen.findByTestId('add-strategy-similarity');
        await fireEvent.mouseEnter(button.parentElement!);

        expect(await screen.findByRole('tooltip')).toHaveTextContent('No query tag selected');
    });

    it('hides the tooltip when the select closes', async () => {
        render(AddStrategyButton, {
            props: { onAdd: vi.fn() }
        });

        await fireEvent.keyDown(screen.getByTestId('add-strategy-button'), { key: 'Enter' });
        const button = await screen.findByTestId('add-strategy-diversity');
        await fireEvent.mouseEnter(button.parentElement!);
        expect(await screen.findByRole('tooltip')).toBeInTheDocument();

        await fireEvent.pointerUp(button);

        expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
    });
});
