import { fireEvent, render, screen } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { FrameView, SampleView } from '$lib/api/lightly_studio_local';
import CanvasVideoPlayer from './CanvasVideoPlayer.svelte';

vi.mock('$lib/hooks/useHideAnnotations', () => ({
    useHideAnnotations: () => ({
        isHidden: writable(false)
    })
}));

vi.mock('$lib/hooks/useSettings', () => ({
    useSettings: () => ({
        showBoundingBoxesForSegmentationStore: writable(true)
    })
}));

const createFrame = (sampleId: string, frameNumber: number, frameTimestampS: number): FrameView =>
    ({
        sample_id: sampleId,
        frame_number: frameNumber,
        frame_timestamp_s: frameTimestampS,
        sample: {
            sample_id: sampleId,
            collection_id: 'collection-1',
            annotations: [],
            created_at: new Date(0),
            updated_at: new Date(0)
        } satisfies SampleView
    }) as FrameView;

describe('CanvasVideoPlayer', () => {
    let videoFrameCallback:
        | ((now: DOMHighResTimeStamp, metadata: VideoFrameCallbackMetadata) => void)
        | null;

    beforeEach(() => {
        videoFrameCallback = null;
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
                strokeStyle: '',
                fillStyle: '',
                font: '',
                textBaseline: 'top'
            } as unknown as CanvasRenderingContext2D;
        });
        Object.defineProperty(HTMLVideoElement.prototype, 'requestVideoFrameCallback', {
            configurable: true,
            value: vi.fn(
                (
                    callback: (
                        now: DOMHighResTimeStamp,
                        metadata: VideoFrameCallbackMetadata
                    ) => void
                ) => {
                    videoFrameCallback = callback;
                    return 1;
                }
            )
        });
        Object.defineProperty(HTMLVideoElement.prototype, 'cancelVideoFrameCallback', {
            configurable: true,
            value: vi.fn()
        });
    });

    it('renders a hidden video element and a visible canvas', () => {
        const frames = [createFrame('frame-1', 0, 0)];
        const { container } = render(CanvasVideoPlayer, {
            props: {
                src: 'video.mp4',
                frames,
                sampleWidth: 1280,
                sampleHeight: 720
            }
        });

        expect(container.querySelector('video')).toBeTruthy();
        expect(screen.getByTestId('canvas-video-player')).toBeTruthy();
    });

    it('shows a poster before the first frame is drawn', () => {
        const frames = [createFrame('frame-1', 0, 0)];
        const { container } = render(CanvasVideoPlayer, {
            props: {
                src: 'video.mp4',
                frames,
                sampleWidth: 1280,
                sampleHeight: 720,
                poster: 'poster.jpg',
                lazyLoad: true
            }
        });

        expect(container.querySelector('img')?.getAttribute('src')).toBe('poster.jpg');
    });

    it('seeks to the initial frame using the frame index transport', async () => {
        const frames = [createFrame('frame-1', 0, 0), createFrame('frame-2', 1, 0.5)];
        const { container } = render(CanvasVideoPlayer, {
            props: {
                src: 'video.mp4',
                frames,
                sampleWidth: 1280,
                sampleHeight: 720,
                showControls: true,
                initialFrameNumber: 1
            }
        });

        const video = container.querySelector('video') as HTMLVideoElement;
        Object.defineProperty(video, 'duration', {
            configurable: true,
            value: 1
        });

        await fireEvent(video, new Event('loadedmetadata'));

        expect(screen.getByRole('button', { name: 'Play' })).toBeTruthy();
        expect(video.currentTime).toBe(0.5);
    });

    it('keeps paused scrubs on frame-start semantics and seeks into the target window', async () => {
        const frames = [
            createFrame('frame-1', 0, 0),
            createFrame('frame-2', 1, 0.5),
            createFrame('frame-3', 2, 1)
        ];
        const onFrameChange = vi.fn();
        const { container } = render(CanvasVideoPlayer, {
            props: {
                src: 'video.mp4',
                frames,
                sampleWidth: 1280,
                sampleHeight: 720,
                showControls: true,
                onFrameChange
            }
        });

        const slider = screen.getByRole('slider');
        const video = container.querySelector('video') as HTMLVideoElement;
        Object.defineProperty(video, 'duration', {
            configurable: true,
            value: 1.5
        });

        await fireEvent.keyDown(slider, { key: 'ArrowRight' });

        expect(video.currentTime).toBe(0.75);

        await fireEvent(video, new Event('seeked'));

        expect(onFrameChange).toHaveBeenLastCalledWith(
            expect.objectContaining({ sample_id: 'frame-2' })
        );
    });

    it('normalizes pause landing back to the last active playback frame', async () => {
        const frames = [
            createFrame('frame-1', 0, 0),
            createFrame('frame-2', 1, 0.5),
            createFrame('frame-3', 2, 1)
        ];
        const { container } = render(CanvasVideoPlayer, {
            props: {
                src: 'video.mp4',
                frames,
                sampleWidth: 1280,
                sampleHeight: 720,
                showControls: true
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
        videoFrameCallback?.(16, {
            presentedFrames: 1,
            expectedDisplayTime: 16,
            width: 1280,
            height: 720,
            mediaTime: 0.8,
            presentationTime: 16,
            processingDuration: 0
        });

        await fireEvent.click(screen.getByRole('button', { name: 'Pause' }));
        paused = true;
        await fireEvent(video, new Event('pause'));

        expect(video.currentTime).toBe(1.25);
    });
});
