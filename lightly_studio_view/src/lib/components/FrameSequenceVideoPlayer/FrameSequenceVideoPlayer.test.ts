import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { FrameView } from '$lib/api/lightly_studio_local';
import FrameSequenceVideoPlayer from './FrameSequenceVideoPlayer.svelte';

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
    },
    {
        sample_id: 'frame-3',
        frame_number: 2,
        frame_timestamp_s: 1,
        sample: { annotations: [] }
    }
] as unknown as FrameView[];

class MockImage extends EventTarget {
    decoding = 'async';
    onload: null | (() => void) = null;
    onerror: null | (() => void) = null;

    set src(_value: string) {
        queueMicrotask(() => {
            this.onload?.();
            this.dispatchEvent(new Event('load'));
        });
    }
}

describe('FrameSequenceVideoPlayer', () => {
    let rafCallback: FrameRequestCallback | null = null;

    beforeEach(() => {
        rafCallback = null;
        vi.stubGlobal('Image', MockImage as unknown as typeof Image);
        vi.stubGlobal(
            'requestAnimationFrame',
            vi.fn((callback: FrameRequestCallback) => {
                rafCallback = callback;
                return 1;
            })
        );
        vi.stubGlobal('cancelAnimationFrame', vi.fn());
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

    it('renders frame-first controls without a hidden video element', async () => {
        const { container } = render(FrameSequenceVideoPlayer, {
            props: {
                frames,
                sampleWidth: 1280,
                sampleHeight: 720,
                resolveFrameImageUrl: (_frame: FrameView, index: number) =>
                    `mock-frame-${index}.png`,
                durationSeconds: 1.5
            }
        });

        await waitFor(() => {
            expect(screen.getByTestId('canvas-video-player-readout')).toHaveTextContent(
                'Frame 0 / 3'
            );
        });

        await waitFor(() => {
            expect(screen.getByRole('button', { name: 'Play video' })).not.toHaveAttribute(
                'disabled'
            );
        });

        expect(container.querySelector('video')).toBeNull();
        expect(screen.getByRole('button', { name: 'Play video' })).toBeTruthy();
        expect(screen.getByTestId('canvas-video-player-slider')).toBeTruthy();
    });

    it('advances through frame indices while playing', async () => {
        render(FrameSequenceVideoPlayer, {
            props: {
                frames,
                sampleWidth: 1280,
                sampleHeight: 720,
                durationSeconds: 1.5,
                resolveFrameImageUrl: (_frame: FrameView, index: number) =>
                    `mock-frame-${index}.png`,
                testDiagnosticsId: 'detail-player'
            }
        });

        await waitFor(() => {
            expect(screen.getByTestId('canvas-video-player-readout')).toHaveTextContent(
                'Frame 0 / 3'
            );
        });

        await waitFor(() => {
            expect(screen.getByRole('button', { name: 'Play video' })).not.toHaveAttribute(
                'disabled'
            );
        });

        await fireEvent.click(screen.getByRole('button', { name: 'Play video' }));
        await waitFor(() => {
            expect(screen.getByRole('button', { name: 'Pause video' })).toBeTruthy();
        });

        rafCallback?.(100);
        rafCallback?.(700);

        await waitFor(() => {
            expect(screen.getByTestId('canvas-video-player-readout')).toHaveTextContent(
                'Frame 1 / 3'
            );
        });

        expect(screen.getByTestId('video-playback-diagnostics-detail-player')).toHaveTextContent(
            '"renderedFrameIndex":1'
        );
        expect(screen.getByTestId('video-playback-diagnostics-detail-player')).toHaveTextContent(
            '"isPlaying":true'
        );
    });
});
