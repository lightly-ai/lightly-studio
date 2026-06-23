import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { writable } from 'svelte/store';
import '@testing-library/jest-dom';
import ImageSizeControl from './ImageSizeControl.svelte';

const sampleSize = writable({ width: 4, height: 4 });
const updateSampleSize = vi.fn();

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        updateSampleSize,
        sampleSize
    })
}));

describe('ImageSizeControl', () => {
    beforeEach(() => {
        sampleSize.set({ width: 4, height: 4 });
        updateSampleSize.mockClear();
    });

    it('disables zoom out at the default max width (16)', () => {
        sampleSize.set({ width: 16, height: 16 });
        render(ImageSizeControl);

        expect(screen.getByLabelText('Zoom out')).toBeDisabled();
    });

    it('disables zoom in at the minimum width (1)', () => {
        sampleSize.set({ width: 1, height: 1 });
        render(ImageSizeControl);

        expect(screen.getByLabelText('Zoom in')).toBeDisabled();
    });

    it('increases width by one when clicking zoom out', async () => {
        sampleSize.set({ width: 10, height: 10 });
        render(ImageSizeControl);

        await fireEvent.click(screen.getByLabelText('Zoom out'));

        expect(updateSampleSize).toHaveBeenCalledWith(11);
    });

    it('respects a custom max prop', async () => {
        sampleSize.set({ width: 16, height: 16 });
        render(ImageSizeControl, { max: 20 });

        const zoomOut = screen.getByLabelText('Zoom out');
        expect(zoomOut).not.toBeDisabled();

        await fireEvent.click(zoomOut);
        expect(updateSampleSize).toHaveBeenCalledWith(17);
    });

    it('shows the slider by default', () => {
        render(ImageSizeControl);

        expect(screen.getByRole('slider')).toBeInTheDocument();
    });

    it('hides the slider but keeps the zoom buttons when compact', () => {
        render(ImageSizeControl, { compact: true });

        expect(screen.queryByRole('slider')).not.toBeInTheDocument();
        expect(screen.getByLabelText('Zoom in')).toBeInTheDocument();
        expect(screen.getByLabelText('Zoom out')).toBeInTheDocument();
    });

    it('shows tooltips on hover over zoom controls', async () => {
        const user = userEvent.setup();
        render(ImageSizeControl);

        await user.hover(screen.getByLabelText('Zoom out'));
        expect(screen.getByRole('tooltip')).toHaveTextContent('Zoom out.');

        await user.unhover(screen.getByLabelText('Zoom out'));
        await user.hover(screen.getByRole('slider'));
        expect(screen.getByRole('tooltip')).toHaveTextContent('Adjust thumbnail size.');

        await user.unhover(screen.getByRole('slider'));
        await user.hover(screen.getByLabelText('Zoom in'));
        expect(screen.getByRole('tooltip')).toHaveTextContent('Zoom in.');
    });
});
