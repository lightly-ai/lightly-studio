import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import TargetDistributionModeSelect from './TargetDistributionModeSelect.svelte';

describe('TargetDistributionModeSelect', () => {
    beforeEach(() => {
        Element.prototype.scrollIntoView = vi.fn();
    });

    it('shows the current target distribution mode label', () => {
        render(TargetDistributionModeSelect, {
            props: {
                targetDistributionMode: 'uniform',
                onUpdate: vi.fn()
            }
        });

        expect(screen.getByTestId('class-balancing-annotation-source')).toHaveTextContent(
            'Uniform'
        );
    });

    it('shows all target distribution mode options when the trigger is clicked', async () => {
        render(TargetDistributionModeSelect, {
            props: {
                targetDistributionMode: 'uniform',
                onUpdate: vi.fn()
            }
        });

        await fireEvent.keyDown(screen.getByTestId('class-balancing-annotation-source'), {
            key: 'Enter'
        });

        expect(
            await screen.findByTestId('class-balancing-annotation-source-uniform')
        ).toBeInTheDocument();
        expect(screen.getByTestId('class-balancing-annotation-source-input')).toBeInTheDocument();
        expect(
            screen.getByTestId('class-balancing-annotation-source-dictionary')
        ).toBeInTheDocument();
    });

    it('calls onUpdate with the selected target distribution mode', async () => {
        const onUpdate = vi.fn();

        render(TargetDistributionModeSelect, {
            props: {
                targetDistributionMode: 'uniform',
                onUpdate
            }
        });

        await fireEvent.keyDown(screen.getByTestId('class-balancing-annotation-source'), {
            key: 'Enter'
        });
        await fireEvent.pointerUp(
            await screen.findByTestId('class-balancing-annotation-source-input')
        );

        expect(onUpdate).toHaveBeenCalledWith('input');
    });
});
