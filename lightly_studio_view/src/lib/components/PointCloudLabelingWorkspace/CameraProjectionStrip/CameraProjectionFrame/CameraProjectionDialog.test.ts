import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import CameraProjectionDialog from './CameraProjectionDialog.svelte';

const defaultProps = {
    open: true,
    label: 'CAM_FRONT',
    imageUrl: null,
    annotations: [],
    position: { index: 2, total: 5 },
    previousKey: '[',
    nextKey: ']'
};

describe('CameraProjectionDialog', () => {
    it('shows the camera name and position', () => {
        render(CameraProjectionDialog, { props: defaultProps });

        expect(screen.getByText('Camera: CAM_FRONT · 2 / 5')).toBeInTheDocument();
    });

    it('calls onNext from the button and the next key', async () => {
        const onNext = vi.fn();
        render(CameraProjectionDialog, { props: { ...defaultProps, onNext } });

        await fireEvent.click(screen.getByRole('button', { name: 'Next camera' }));
        await fireEvent.keyDown(screen.getByRole('dialog'), { key: ']' });

        expect(onNext).toHaveBeenCalledTimes(2);
    });

    it('disables the buttons without callbacks', () => {
        render(CameraProjectionDialog, { props: defaultProps });

        expect(screen.getByRole('button', { name: 'Previous camera' })).toBeDisabled();
        expect(screen.getByRole('button', { name: 'Next camera' })).toBeDisabled();
    });

    it('toggles playback on Space but not on the camera key', async () => {
        const onPlaybackToggle = vi.fn();
        render(CameraProjectionDialog, { props: { ...defaultProps, onPlaybackToggle } });
        const dialog = screen.getByRole('dialog');

        await fireEvent.keyDown(dialog, { key: ']' });
        expect(onPlaybackToggle).not.toHaveBeenCalled();

        await fireEvent.keyDown(dialog, { key: ' ', code: 'Space' });
        expect(onPlaybackToggle).toHaveBeenCalledTimes(1);
    });
});
