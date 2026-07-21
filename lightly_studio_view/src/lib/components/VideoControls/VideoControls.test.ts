import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import VideoControls from './VideoControls.svelte';

function baseProps(overrides = {}) {
    return {
        currentTimeS: 0,
        durationS: 20,
        isPlaying: false,
        isMuted: false,
        isFullscreen: false,
        onPlayPause: vi.fn(),
        onSeek: vi.fn(),
        onToggleMute: vi.fn(),
        onToggleFullscreen: vi.fn(),
        ...overrides
    };
}

describe('VideoControls', () => {
    it('shows the play affordance when paused and calls onPlayPause', async () => {
        const onPlayPause = vi.fn();
        const { getByLabelText } = render(VideoControls, {
            props: baseProps({ isPlaying: false, onPlayPause })
        });

        const button = getByLabelText('Play');
        await fireEvent.click(button);
        expect(onPlayPause).toHaveBeenCalledOnce();
    });

    it('shows the pause affordance while playing', () => {
        const { getByLabelText } = render(VideoControls, { props: baseProps({ isPlaying: true }) });
        expect(getByLabelText('Pause')).toBeTruthy();
    });

    it('renders elapsed and total time', () => {
        const { getByText } = render(VideoControls, {
            props: baseProps({ currentTimeS: 65, durationS: 130 })
        });
        expect(getByText('1:05 / 2:10')).toBeTruthy();
    });

    function mockScrubberGeometry(scrubber: HTMLElement) {
        scrubber.setPointerCapture = vi.fn();
        scrubber.hasPointerCapture = vi.fn(() => true);
        scrubber.releasePointerCapture = vi.fn();
        vi.spyOn(scrubber, 'getBoundingClientRect').mockReturnValue({
            left: 0,
            width: 100,
            top: 0,
            height: 12,
            right: 100,
            bottom: 12,
            x: 0,
            y: 0,
            toJSON: () => ({})
        } as DOMRect);
    }

    it('seeks to the clicked position on the scrubber', async () => {
        const onSeek = vi.fn();
        const { getByRole } = render(VideoControls, {
            props: baseProps({ durationS: 20, onSeek })
        });

        const scrubber = getByRole('slider');
        mockScrubberGeometry(scrubber);

        // jsdom's PointerEvent drops clientX; MouseEvent carries it.
        scrubber.dispatchEvent(new MouseEvent('pointerdown', { clientX: 25, bubbles: true }));
        // 25% of 20s → 5s
        expect(onSeek).toHaveBeenCalledWith(5);
    });

    it('stops seeking after the pointer gesture is cancelled', async () => {
        const onSeek = vi.fn();
        const { getByRole } = render(VideoControls, {
            props: baseProps({ durationS: 20, onSeek })
        });

        const scrubber = getByRole('slider');
        mockScrubberGeometry(scrubber);

        scrubber.dispatchEvent(new MouseEvent('pointerdown', { clientX: 25, bubbles: true }));
        scrubber.dispatchEvent(new MouseEvent('pointercancel', { bubbles: true }));
        onSeek.mockClear();

        scrubber.dispatchEvent(new MouseEvent('pointermove', { clientX: 75, bubbles: true }));
        expect(onSeek).not.toHaveBeenCalled();
    });

    it('seeks with the keyboard arrows', async () => {
        const onSeek = vi.fn();
        const { getByRole } = render(VideoControls, {
            props: baseProps({ currentTimeS: 10, durationS: 20, onSeek })
        });

        const scrubber = getByRole('slider');
        await fireEvent.keyDown(scrubber, { key: 'ArrowRight' });
        expect(onSeek).toHaveBeenCalledWith(15);

        await fireEvent.keyDown(scrubber, { key: 'ArrowLeft' });
        expect(onSeek).toHaveBeenCalledWith(5);
    });

    it('caps the arrow-key step on short clips instead of leaping to the end', async () => {
        const onSeek = vi.fn();
        const { getByRole } = render(VideoControls, {
            props: baseProps({ currentTimeS: 0, durationS: 4, onSeek })
        });

        const scrubber = getByRole('slider');
        // Step is capped to durationS / 4 = 1s, not the default 5s.
        await fireEvent.keyDown(scrubber, { key: 'ArrowRight' });
        expect(onSeek).toHaveBeenCalledWith(1);
    });

    it('calls mute and fullscreen callbacks', async () => {
        const onToggleMute = vi.fn();
        const onToggleFullscreen = vi.fn();
        const { getByLabelText } = render(VideoControls, {
            props: baseProps({ onToggleMute, onToggleFullscreen })
        });

        await fireEvent.click(getByLabelText('Mute'));
        await fireEvent.click(getByLabelText('Full screen'));
        expect(onToggleMute).toHaveBeenCalledOnce();
        expect(onToggleFullscreen).toHaveBeenCalledOnce();
    });
});
