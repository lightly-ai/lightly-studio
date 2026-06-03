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
});
