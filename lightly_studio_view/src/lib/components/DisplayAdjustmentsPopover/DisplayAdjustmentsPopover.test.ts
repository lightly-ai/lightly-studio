import { fireEvent, render, screen } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';

const imageBrightness = writable(1);
const imageContrast = writable(1);
const maskOpacity = writable(0.6);

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        imageBrightness,
        imageContrast,
        maskOpacity
    })
}));

import DisplayAdjustmentsPopover from './DisplayAdjustmentsPopover.svelte';

describe('DisplayAdjustmentsPopover', () => {
    it('renders the trigger button', () => {
        render(DisplayAdjustmentsPopover);
        expect(screen.getByTestId('display-adjustments-trigger')).toBeInTheDocument();
    });

    it('opens popover with sliders on click', async () => {
        render(DisplayAdjustmentsPopover);
        await fireEvent.click(screen.getByTestId('display-adjustments-trigger'));

        expect(screen.getByRole('slider', { name: 'Brightness' })).toBeInTheDocument();
        expect(screen.getByRole('slider', { name: 'Contrast' })).toBeInTheDocument();
        expect(screen.getByRole('slider', { name: 'Mask opacity' })).toBeInTheDocument();
    });

    it('disables reset button when all values are at defaults', async () => {
        imageBrightness.set(1);
        imageContrast.set(1);
        maskOpacity.set(0.6);

        render(DisplayAdjustmentsPopover);
        await fireEvent.click(screen.getByTestId('display-adjustments-trigger'));

        expect(screen.getByRole('button', { name: 'Reset display adjustments' })).toBeDisabled();
    });

    it('enables reset button when a value differs from default', async () => {
        imageBrightness.set(1.5);
        imageContrast.set(1);
        maskOpacity.set(0.6);

        render(DisplayAdjustmentsPopover);
        await fireEvent.click(screen.getByTestId('display-adjustments-trigger'));

        expect(screen.getByRole('button', { name: 'Reset display adjustments' })).toBeEnabled();
    });

    it('resets all values to defaults on reset click', async () => {
        imageBrightness.set(1.5);
        imageContrast.set(0.5);
        maskOpacity.set(0.2);

        render(DisplayAdjustmentsPopover);
        await fireEvent.click(screen.getByTestId('display-adjustments-trigger'));
        await fireEvent.click(screen.getByRole('button', { name: 'Reset display adjustments' }));

        const sliders = screen.getAllByRole('slider');
        expect(sliders.map((s) => Number(s.getAttribute('aria-valuenow')))).toEqual([1, 1, 0.6]);
    });
});
