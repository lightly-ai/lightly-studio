import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import type { FrameView } from '$lib/api/lightly_studio_local';
import { createVideoPlaybackController } from './videoPlaybackController';

class MockVideoElement extends EventTarget {
    currentTime = 0;
    paused = true;
    ended = false;
    private rvfcHandle = 0;
    requestVideoFrameCallback = vi.fn(
        (callback: (now: number, metadata: VideoFrameCallbackMetadata) => void) => {
            this.rvfcHandle += 1;
            this.rvfcCallback = callback;
            return this.rvfcHandle;
        }
    );
    cancelVideoFrameCallback = vi.fn();
    rvfcCallback: ((now: number, metadata: VideoFrameCallbackMetadata) => void) | null = null;
}

const frames: FrameView[] = [
    {
        sample_id: 'frame-1',
        frame_number: 0,
        frame_timestamp_s: 0,
        sample: {} as FrameView['sample']
    } as FrameView,
    {
        sample_id: 'frame-2',
        frame_number: 1,
        frame_timestamp_s: 0.5,
        sample: {} as FrameView['sample']
    } as FrameView
];

describe('createVideoPlaybackController', () => {
    let rafCallback: FrameRequestCallback | null = null;

    beforeEach(() => {
        rafCallback = null;
        vi.stubGlobal(
            'requestAnimationFrame',
            vi.fn((callback: FrameRequestCallback) => {
                rafCallback = callback;
                return 1;
            })
        );
        vi.stubGlobal('cancelAnimationFrame', vi.fn());
        vi.spyOn(performance, 'now').mockReturnValue(123);
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        vi.restoreAllMocks();
    });

    it('uses requestVideoFrameCallback while playing', () => {
        const videoEl = new MockVideoElement();
        videoEl.paused = false;
        const onSample = vi.fn();

        const controller = createVideoPlaybackController({
            videoEl: videoEl as unknown as HTMLVideoElement,
            frames,
            onSample
        });

        expect(videoEl.requestVideoFrameCallback).toHaveBeenCalledTimes(1);

        videoEl.currentTime = 0.5;
        videoEl.rvfcCallback?.(33, {
            expectedDisplayTime: 33,
            height: 1,
            mediaTime: 0.5,
            presentedFrames: 1,
            presentationTime: 33,
            processingDuration: 0,
            width: 1
        });

        expect(onSample).toHaveBeenCalledWith(
            expect.objectContaining({
                source: 'rvfc',
                mediaTime: 0.5
            })
        );

        controller.destroy();
    });

    it('falls back to requestAnimationFrame when rvfc is unavailable', () => {
        const videoEl = new MockVideoElement();
        delete (videoEl as Partial<MockVideoElement>).requestVideoFrameCallback;
        delete (videoEl as Partial<MockVideoElement>).cancelVideoFrameCallback;
        videoEl.paused = false;
        videoEl.currentTime = 0.1;
        const onSample = vi.fn();

        createVideoPlaybackController({
            videoEl: videoEl as unknown as HTMLVideoElement,
            frames,
            onSample
        });

        expect(requestAnimationFrame).toHaveBeenCalled();
        rafCallback?.(16);
        expect(onSample).toHaveBeenCalledWith(
            expect.objectContaining({
                source: 'raf'
            })
        );
    });

    it('can force requestAnimationFrame even when rvfc is available', () => {
        const videoEl = new MockVideoElement();
        videoEl.paused = false;
        videoEl.currentTime = 0.1;
        const onSample = vi.fn();

        createVideoPlaybackController({
            videoEl: videoEl as unknown as HTMLVideoElement,
            frames,
            clockMode: 'raf',
            onSample
        });

        expect(videoEl.requestVideoFrameCallback).not.toHaveBeenCalled();
        expect(requestAnimationFrame).toHaveBeenCalled();

        rafCallback?.(16);
        expect(onSample).toHaveBeenCalledWith(
            expect.objectContaining({
                source: 'raf'
            })
        );
    });

    it('syncs immediately on seeked, pause, and ended', () => {
        const videoEl = new MockVideoElement();
        const onSample = vi.fn();

        createVideoPlaybackController({
            videoEl: videoEl as unknown as HTMLVideoElement,
            frames,
            onSample
        });

        videoEl.currentTime = 0.1;
        videoEl.dispatchEvent(new Event('seeked'));
        videoEl.currentTime = 0.6;
        videoEl.dispatchEvent(new Event('pause'));
        videoEl.dispatchEvent(new Event('ended'));

        expect(onSample).toHaveBeenCalledTimes(2);
        expect(onSample).toHaveBeenNthCalledWith(
            1,
            expect.objectContaining({
                source: 'event',
                currentTime: 0.1
            })
        );
        expect(onSample).toHaveBeenNthCalledWith(
            2,
            expect.objectContaining({
                source: 'event',
                currentTime: 0.6
            })
        );
    });

    it('does not emit duplicate frames while time stays in the same annotation interval', () => {
        const videoEl = new MockVideoElement();
        const onSample = vi.fn();

        createVideoPlaybackController({
            videoEl: videoEl as unknown as HTMLVideoElement,
            frames,
            onSample
        });

        videoEl.currentTime = 0.1;
        videoEl.dispatchEvent(new Event('loadeddata'));
        videoEl.currentTime = 0.2;
        videoEl.dispatchEvent(new Event('seeked'));

        expect(onSample).toHaveBeenCalledTimes(1);
    });

    it('can emit duplicate samples when requested for same-surface playback', () => {
        const videoEl = new MockVideoElement();
        const onSample = vi.fn();

        createVideoPlaybackController({
            videoEl: videoEl as unknown as HTMLVideoElement,
            frames,
            emitDuplicateFrames: true,
            onSample
        });

        videoEl.currentTime = 0.1;
        videoEl.dispatchEvent(new Event('loadeddata'));
        videoEl.currentTime = 0.2;
        videoEl.dispatchEvent(new Event('seeked'));

        expect(onSample).toHaveBeenCalledTimes(2);
    });

    it('can resolve selection strategy per playback source', () => {
        const videoEl = new MockVideoElement();
        videoEl.paused = false;
        const onSample = vi.fn();

        createVideoPlaybackController({
            videoEl: videoEl as unknown as HTMLVideoElement,
            frames,
            selectionStrategy: ({ source }) => (source === 'event' ? 'frame_start' : 'midpoint'),
            onSample
        });

        videoEl.currentTime = 0.49;
        videoEl.dispatchEvent(new Event('seeked'));
        videoEl.rvfcCallback?.(33, {
            expectedDisplayTime: 33,
            height: 1,
            mediaTime: 0.49,
            presentedFrames: 1,
            presentationTime: 33,
            processingDuration: 0,
            width: 1
        });

        expect(onSample).toHaveBeenNthCalledWith(
            1,
            expect.objectContaining({
                selection: expect.objectContaining({
                    strategy: 'frame_start',
                    frame: frames[0]
                })
            })
        );
        expect(onSample).toHaveBeenNthCalledWith(
            2,
            expect.objectContaining({
                selection: expect.objectContaining({
                    strategy: 'midpoint',
                    frame: frames[1]
                })
            })
        );
    });

    it('cancels scheduled callbacks on destroy', () => {
        const videoEl = new MockVideoElement();
        videoEl.paused = false;

        const controller = createVideoPlaybackController({
            videoEl: videoEl as unknown as HTMLVideoElement,
            frames,
            onSample: vi.fn()
        });

        controller.destroy();

        expect(videoEl.cancelVideoFrameCallback).toHaveBeenCalled();
    });
});
