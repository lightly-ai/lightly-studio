import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import CameraProjectionDialog from './CameraProjectionDialog.svelte';
import { DEFAULT_PROJECTION_SETTINGS } from '../projectionSettings';

const defaultProps = {
    open: true,
    label: 'CAM_FRONT',
    imageUrl: null,
    overlay: { annotations: [] },
    position: { index: 2, total: 5 },
    previousKey: '[',
    nextKey: ']'
};

describe('CameraProjectionDialog', () => {
    it('shows the camera name and position', () => {
        render(CameraProjectionDialog, { props: defaultProps });

        expect(screen.getByText('Camera: CAM_FRONT · 2 / 5')).toBeInTheDocument();
    });

    it('calls onNext from the button', async () => {
        const onNext = vi.fn();
        render(CameraProjectionDialog, { props: { ...defaultProps, onNext } });

        await fireEvent.click(screen.getByRole('button', { name: 'Next camera' }));

        expect(onNext).toHaveBeenCalledTimes(1);
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

    it('focuses the dialog so Space toggles playback once', async () => {
        const onPlaybackToggle = vi.fn();
        const windowKeydown = vi.fn();
        window.addEventListener('keydown', windowKeydown);
        render(CameraProjectionDialog, { props: { ...defaultProps, onPlaybackToggle } });
        await waitFor(() => expect(document.activeElement).toBe(screen.getByRole('dialog')));

        await fireEvent.keyDown(document.activeElement as HTMLElement, {
            key: ' ',
            code: 'Space'
        });

        expect(onPlaybackToggle).toHaveBeenCalledTimes(1);
        expect(windowKeydown).not.toHaveBeenCalled();
        window.removeEventListener('keydown', windowKeydown);
    });

    it('updates the image while the dialog stays open', async () => {
        const { rerender } = render(CameraProjectionDialog, {
            props: { ...defaultProps, imageUrl: 'http://api.test/a.jpg' }
        });
        const image = screen.getByRole('img', { name: 'CAM_FRONT enlarged' });
        expect(image).toHaveAttribute('src', 'http://api.test/a.jpg');

        await rerender({ ...defaultProps, imageUrl: 'http://api.test/b.jpg' });

        expect(screen.getByRole('img', { name: 'CAM_FRONT enlarged' })).toBe(image);
        expect(image).toHaveAttribute('src', 'http://api.test/b.jpg');
    });

    it('does not restore focus to the opener when it closes', async () => {
        const opener = document.createElement('button');
        document.body.appendChild(opener);
        opener.focus();
        render(CameraProjectionDialog, { props: defaultProps });

        const close = screen.getByRole('button', { name: 'Close' });
        close.focus();
        await fireEvent.click(close);

        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
        expect(document.activeElement).not.toBe(opener);
        opener.remove();
    });

    it('shows projection settings when settings are given', () => {
        render(CameraProjectionDialog, {
            props: {
                ...defaultProps,
                projectionSettings: DEFAULT_PROJECTION_SETTINGS,
                onProjectionSettingsChange: vi.fn()
            }
        });

        expect(screen.getByRole('button', { name: 'Projection settings' })).toBeInTheDocument();
    });

    it('toggles playback from Space on a dialog control without opening it', async () => {
        const onPlaybackToggle = vi.fn();
        render(CameraProjectionDialog, {
            props: {
                ...defaultProps,
                onPlaybackToggle,
                projectionSettings: DEFAULT_PROJECTION_SETTINGS,
                onProjectionSettingsChange: vi.fn()
            }
        });

        const settingsButton = screen.getByRole('button', { name: 'Projection settings' });
        await fireEvent.keyDown(settingsButton, { code: 'Space', key: ' ' });
        await new Promise((resolve) => setTimeout(resolve, 0));

        expect(onPlaybackToggle).toHaveBeenCalledOnce();
        expect(settingsButton).toHaveAttribute('aria-expanded', 'false');
        expect(document.activeElement).not.toBe(settingsButton);
    });
});
