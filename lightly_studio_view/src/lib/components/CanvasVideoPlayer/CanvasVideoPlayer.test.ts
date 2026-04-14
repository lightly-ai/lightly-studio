import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { FrameView } from '$lib/api/lightly_studio_local';
import CanvasVideoPlayer from './CanvasVideoPlayer.svelte';

const frames = [
    {
        sample_id: 'frame-1',
        frame_number: 0,
        frame_timestamp_s: 0,
        sample: { annotations: [] }
    },
    {
        sample_id: 'frame-2',
        frame_number: 1,
        frame_timestamp_s: 0.5,
        sample: { annotations: [] }
    }
] as unknown as FrameView[];

const queuedSeekFrames = [
    {
        sample_id: 'frame-1',
        frame_number: 0,
        frame_timestamp_s: 0,
        sample: { annotations: [] }
    },
    {
        sample_id: 'frame-2',
        frame_number: 1,
        frame_timestamp_s: 0.5,
        sample: { annotations: [] }
    },
    {
        sample_id: 'frame-3',
        frame_number: 2,
        frame_timestamp_s: 1,
        sample: { annotations: [] }
    }
] as unknown as FrameView[];

describe('CanvasVideoPlayer', () => {
    beforeEach(() => {
        vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue(undefined);
        vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(() => {});
        vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(() => {
            return {
                clearRect: vi.fn(),
                drawImage: vi.fn(),
                putImageData: vi.fn(),
                strokeRect: vi.fn(),
                save: vi.fn(),
                restore: vi.fn(),
                lineWidth: 1,
                strokeStyle: ''
            } as unknown as CanvasRenderingContext2D;
        });
    });

    it('renders custom controls and no native visible controls', () => {
        const { container } = render(CanvasVideoPlayer, {
            props: {
                src: 'video.mp4',
                frames,
                sampleWidth: 1280,
                sampleHeight: 720
            }
        });

        expect(screen.getByRole('button', { name: 'Play video' })).toBeTruthy();
        expect(screen.getByTestId('canvas-video-player-slider')).toBeTruthy();
        expect(screen.queryByTestId('video-playback-debug')).toBeNull();
        expect(screen.getByTestId('canvas-video-player-readout')).toHaveTextContent('Frame 0 / 2');
        expect(screen.getByTestId('canvas-video-player-readout')).toHaveTextContent(
            '0.000s / 0.500s'
        );

        const video = container.querySelector('video');
        expect(video?.hasAttribute('controls')).toBe(false);
        expect(container.querySelector('input[type="range"]')).toBeNull();
    });

    it('publishes hidden diagnostics when a test diagnostics id is provided', () => {
        render(CanvasVideoPlayer, {
            props: {
                src: 'video.mp4',
                frames,
                sampleWidth: 1280,
                sampleHeight: 720,
                testDiagnosticsId: 'detail-player'
            }
        });

        expect(screen.getByTestId('video-playback-diagnostics-detail-player')).toHaveTextContent(
            '"playerId":"detail-player"'
        );
        expect(screen.getByTestId('video-playback-diagnostics-detail-player')).toHaveTextContent(
            '"selectedFrameIndex":0'
        );
    });

    it('renders temporary selection mode buttons and defaults to hybrid when enabled', () => {
        render(CanvasVideoPlayer, {
            props: {
                src: 'video.mp4',
                frames,
                sampleWidth: 1280,
                sampleHeight: 720,
                showDebug: true,
                showSelectionModeDebugControls: true,
                selectionModeOverride: 'hybrid'
            }
        });

        expect(screen.getByTestId('selection-mode-debug-controls')).toBeTruthy();
        expect(screen.getByRole('button', { name: 'start' })).toHaveAttribute(
            'aria-pressed',
            'false'
        );
        expect(screen.getByRole('button', { name: 'mid' })).toHaveAttribute(
            'aria-pressed',
            'false'
        );
        expect(screen.getByRole('button', { name: 'hybrid' })).toHaveAttribute(
            'aria-pressed',
            'true'
        );
        expect(screen.getByTestId('video-playback-debug')).toHaveTextContent('override: hybrid');
        expect(screen.getByTestId('video-playback-debug')).toHaveTextContent('mode: frame_start');
    });

    it('plays the hidden video from the custom play button', async () => {
        render(CanvasVideoPlayer, {
            props: {
                src: 'video.mp4',
                frames,
                sampleWidth: 1280,
                sampleHeight: 720
            }
        });

        await fireEvent.click(screen.getByRole('button', { name: 'Play video' }));

        expect(HTMLMediaElement.prototype.play).toHaveBeenCalled();
    });

    it('waits for seek resolution before updating the transport frame', async () => {
        const onSeek = vi.fn();
        const { container } = render(CanvasVideoPlayer, {
            props: {
                src: 'video.mp4',
                frames,
                sampleWidth: 1280,
                sampleHeight: 720,
                onSeek
            }
        });

        const slider = screen.getByRole('slider');
        const video = container.querySelector('video') as HTMLVideoElement;
        Object.defineProperty(video, 'duration', {
            configurable: true,
            value: 1
        });

        await fireEvent.keyDown(slider, { key: 'ArrowRight' });

        expect(video.currentTime).toBe(0.75);
        expect(onSeek).toHaveBeenCalledWith(1);
        expect(screen.getByTestId('canvas-video-player-readout')).toHaveTextContent('Frame 1 / 2');

        await fireEvent(video, new Event('seeked'));

        expect(screen.getByTestId('canvas-video-player-readout')).toHaveTextContent('Frame 1 / 2');
    });

    it('serializes scrubbing requests and finishes on the latest queued frame', async () => {
        const onSeek = vi.fn();
        const { container } = render(CanvasVideoPlayer, {
            props: {
                src: 'video.mp4',
                frames: queuedSeekFrames,
                sampleWidth: 1280,
                sampleHeight: 720,
                onSeek
            }
        });

        const slider = screen.getByRole('slider');
        const video = container.querySelector('video') as HTMLVideoElement;
        Object.defineProperty(video, 'duration', {
            configurable: true,
            value: 1.5
        });

        await fireEvent.keyDown(slider, { key: 'ArrowRight' });
        await fireEvent.keyDown(slider, { key: 'End' });

        expect(screen.getByTestId('canvas-video-player-readout')).toHaveTextContent('Frame 2 / 3');
        expect(onSeek).toHaveBeenLastCalledWith(2);

        await fireEvent(video, new Event('seeked'));

        expect(video.currentTime).toBeGreaterThan(1);
        expect(screen.getByTestId('canvas-video-player-readout')).toHaveTextContent('Frame 2 / 3');

        await fireEvent(video, new Event('seeked'));

        expect(screen.getByTestId('canvas-video-player-readout')).toHaveTextContent('Frame 2 / 3');
    });

    it('clears the paused frame pin when playback resumes', async () => {
        const { container } = render(CanvasVideoPlayer, {
            props: {
                src: 'video.mp4',
                frames,
                sampleWidth: 1280,
                sampleHeight: 720,
                showDebug: true
            }
        });

        const slider = screen.getByRole('slider');
        const video = container.querySelector('video') as HTMLVideoElement;
        Object.defineProperty(video, 'duration', {
            configurable: true,
            value: 1
        });

        await fireEvent.keyDown(slider, { key: 'ArrowRight' });
        expect(screen.getByTestId('canvas-video-player-readout')).toHaveTextContent('Frame 1 / 2');

        await fireEvent(video, new Event('play'));
        await fireEvent(video, new Event('pause'));

        expect(screen.getByTestId('video-playback-debug')).toHaveTextContent('pinned_frame: -');
    });

    it('normalizes pause landings to the last active playback frame', async () => {
        const { container } = render(CanvasVideoPlayer, {
            props: {
                src: 'video.mp4',
                frames: queuedSeekFrames,
                sampleWidth: 1280,
                sampleHeight: 720,
                showDebug: true,
                selectionModeOverride: 'mid'
            }
        });

        const video = container.querySelector('video') as HTMLVideoElement;
        let paused = true;
        Object.defineProperty(video, 'paused', {
            configurable: true,
            get: () => paused
        });
        Object.defineProperty(video, 'duration', {
            configurable: true,
            value: 1.5
        });

        paused = false;
        video.currentTime = 0.8;
        await fireEvent(video, new Event('play'));
        await fireEvent(video, new Event('seeked'));

        await fireEvent.click(screen.getByRole('button', { name: 'Pause video' }));
        paused = true;
        await fireEvent(video, new Event('pause'));

        expect(video.currentTime).toBe(1.25);
        expect(screen.getByTestId('video-playback-debug')).toHaveTextContent('pinned_frame: 2');

        await fireEvent(video, new Event('seeked'));

        expect(screen.getByTestId('canvas-video-player-readout')).toHaveTextContent('Frame 2 / 3');
        expect(screen.getByTestId('video-playback-debug')).toHaveTextContent('mode: frame_start');
    });

    it('switches selection strategies from the temporary debug buttons', async () => {
        render(CanvasVideoPlayer, {
            props: {
                src: 'video.mp4',
                frames,
                sampleWidth: 1280,
                sampleHeight: 720,
                showDebug: true,
                showSelectionModeDebugControls: true,
                selectionModeOverride: 'hybrid'
            }
        });

        await fireEvent.click(screen.getByRole('button', { name: 'mid' }));
        expect(screen.getByTestId('video-playback-debug')).toHaveTextContent('override: mid');
        expect(screen.getByTestId('video-playback-debug')).toHaveTextContent('mode: midpoint');

        await fireEvent.click(screen.getByRole('button', { name: 'start' }));
        expect(screen.getByTestId('video-playback-debug')).toHaveTextContent('override: start');
        expect(screen.getByTestId('video-playback-debug')).toHaveTextContent('mode: frame_start');
    });

    it('can hide controls and show debug when configured for previews', () => {
        render(CanvasVideoPlayer, {
            props: {
                src: 'video.mp4',
                frames,
                sampleWidth: 1280,
                sampleHeight: 720,
                showControls: false,
                showDebug: true,
                loop: true
            }
        });

        expect(screen.queryByRole('button', { name: 'Play video' })).toBeNull();
        expect(screen.queryByRole('slider', { name: 'Seek video frame' })).toBeNull();
        expect(screen.getByTestId('video-playback-debug')).toBeTruthy();
    });
});
