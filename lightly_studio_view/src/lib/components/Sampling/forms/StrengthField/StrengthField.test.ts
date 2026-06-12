import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import StrengthField from './StrengthField.svelte';

describe('StrengthField', () => {
    it('renders the strength input with the current value', () => {
        render(StrengthField, {
            props: {
                strength: 2.5,
                id: 'test-strength',
                testid: 'test-strength-input',
                onUpdate: vi.fn()
            }
        });

        expect(screen.getByTestId('test-strength-input')).toHaveValue(2.5);
    });

    it('calls onUpdate with the new strength value', async () => {
        const onUpdate = vi.fn();

        render(StrengthField, {
            props: {
                strength: 1,
                id: 'test-strength',
                testid: 'test-strength-input',
                onUpdate
            }
        });

        await fireEvent.input(screen.getByTestId('test-strength-input'), {
            target: { value: '3' }
        });

        expect(onUpdate).toHaveBeenCalledWith(3);
    });

    it('calls onUpdate with a negative strength value', async () => {
        const onUpdate = vi.fn();

        render(StrengthField, {
            props: {
                strength: 1,
                id: 'test-strength',
                testid: 'test-strength-input',
                onUpdate
            }
        });

        await fireEvent.input(screen.getByTestId('test-strength-input'), {
            target: { value: '-1' }
        });

        expect(onUpdate).toHaveBeenCalledWith(-1);
    });

    it('does not call onUpdate when the input is empty', async () => {
        const onUpdate = vi.fn();

        render(StrengthField, {
            props: {
                strength: 1,
                id: 'test-strength',
                testid: 'test-strength-input',
                onUpdate
            }
        });

        await fireEvent.input(screen.getByTestId('test-strength-input'), {
            target: { value: '' }
        });

        expect(onUpdate).not.toHaveBeenCalled();
    });

    it('does not call onUpdate with a negative value when min is 0', async () => {
        const onUpdate = vi.fn();

        render(StrengthField, {
            props: {
                strength: 1,
                id: 'test-strength',
                testid: 'test-strength-input',
                min: 0,
                onUpdate
            }
        });

        await fireEvent.input(screen.getByTestId('test-strength-input'), {
            target: { value: '-1' }
        });

        expect(onUpdate).not.toHaveBeenCalled();
    });

    it('calls onUpdate with a non-negative value when min is 0', async () => {
        const onUpdate = vi.fn();

        render(StrengthField, {
            props: {
                strength: 1,
                id: 'test-strength',
                testid: 'test-strength-input',
                min: 0,
                onUpdate
            }
        });

        await fireEvent.input(screen.getByTestId('test-strength-input'), {
            target: { value: '2' }
        });

        expect(onUpdate).toHaveBeenCalledWith(2);
    });

    it('shows tooltip mentioning negative values when min is not set', async () => {
        render(StrengthField, {
            props: {
                strength: 1,
                id: 'test-strength',
                testid: 'test-strength-input',
                onUpdate: vi.fn()
            }
        });

        await fireEvent.mouseEnter(screen.getByRole('button', { name: 'More information' }));

        expect(screen.getByRole('tooltip')).toHaveTextContent(
            'Negative values invert the scoring direction.'
        );
    });

    it('shows tooltip without negative values mention when min is 0', async () => {
        render(StrengthField, {
            props: {
                strength: 1,
                id: 'test-strength',
                testid: 'test-strength-input',
                min: 0,
                onUpdate: vi.fn()
            }
        });

        await fireEvent.mouseEnter(screen.getByRole('button', { name: 'More information' }));

        expect(screen.getByRole('tooltip')).not.toHaveTextContent(
            'Negative values invert the scoring direction.'
        );
    });
});
