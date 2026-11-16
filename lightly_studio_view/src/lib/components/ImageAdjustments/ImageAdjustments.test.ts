import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import ImageAdjustments from './ImageAdjustments.svelte';

const defaultProps = { brightness: 1, contrast: 1, maskOpacity: 0.6 };

const sliderValues = () =>
    screen.getAllByRole('slider').map((thumb) => Number(thumb.getAttribute('aria-valuenow')));

describe('ImageAdjustments', () => {
    it('renders named sliders and a disabled reset button at the defaults', () => {
        render(ImageAdjustments, { props: defaultProps });

        expect(screen.getByRole('slider', { name: 'Brightness' })).toBeInTheDocument();
        expect(screen.getByRole('slider', { name: 'Contrast' })).toBeInTheDocument();
        expect(screen.getByRole('slider', { name: 'Mask opacity' })).toBeInTheDocument();
        expect(sliderValues()).toEqual([1, 1, 0.6]);
        expect(screen.getByRole('button', { name: 'Reset image adjustments' })).toBeDisabled();
    });

    it('resets all values to their defaults', async () => {
        render(ImageAdjustments, {
            props: { brightness: 1.5, contrast: 0.5, maskOpacity: 0.2 }
        });
        const resetButton = screen.getByRole('button', { name: 'Reset image adjustments' });
        expect(resetButton).toBeEnabled();

        await fireEvent.click(resetButton);

        expect(sliderValues()).toEqual([1, 1, 0.6]);
        expect(resetButton).toBeDisabled();
    });
});
