import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import SampleCountInput from './SampleCountInput.svelte';

describe('SampleCountInput', () => {
    it('renders the count input with the given count value', () => {
        render(SampleCountInput, {
            count: 42,
            percentage: 0,
            onCountChange: vi.fn(),
            onPercentageChange: vi.fn()
        });

        expect(screen.getByTestId('sampling-dialog-n-samples-input')).toHaveValue(42);
    });

    it('renders the percentage input with the given percentage value', () => {
        render(SampleCountInput, {
            count: 0,
            percentage: 25,
            onCountChange: vi.fn(),
            onPercentageChange: vi.fn()
        });

        expect(screen.getByTestId('sampling-dialog-n-samples-percentage-input')).toHaveValue(25);
    });

    it('calls onCountChange with the entered value when the count input changes', async () => {
        const onCountChange = vi.fn();

        render(SampleCountInput, {
            count: 10,
            percentage: 0,
            onCountChange,
            onPercentageChange: vi.fn()
        });

        await fireEvent.input(screen.getByTestId('sampling-dialog-n-samples-input'), {
            target: { value: '500' }
        });

        expect(onCountChange).toHaveBeenCalledWith(500);
    });

    it('calls onPercentageChange with the entered value when the percentage input changes', async () => {
        const onPercentageChange = vi.fn();

        render(SampleCountInput, {
            count: 0,
            percentage: 10,
            onCountChange: vi.fn(),
            onPercentageChange
        });

        await fireEvent.input(screen.getByTestId('sampling-dialog-n-samples-percentage-input'), {
            target: { value: '20' }
        });

        expect(onPercentageChange).toHaveBeenCalledWith(20);
    });

    it('displays the % suffix label', () => {
        render(SampleCountInput, {
            count: 0,
            percentage: 0,
            onCountChange: vi.fn(),
            onPercentageChange: vi.fn()
        });

        expect(screen.getByText('%')).toBeInTheDocument();
    });
});
