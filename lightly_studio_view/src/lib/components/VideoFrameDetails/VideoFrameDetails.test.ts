import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
import VideoFrameDetails from './VideoFrameDetails.svelte';
import type { VideoView, SampleView } from '$lib/api/lightly_studio_local';
import * as useVideoFramesModule from '$lib/hooks/useVideoFrames/useVideoFrames';
import { writable, get } from 'svelte/store';

vi.mock('$lib/hooks/useVideoFrames/useVideoFrames', () => ({
    useVideoFrames: vi.fn()
}));

describe('VideoFrameDetails', () => {
    const mockSample: SampleView = {
        collection_id: 'video-collection-1',
        sample_id: 'video-1',
        created_at: new Date(0),
        updated_at: new Date(0)
    };

    const mockFrameSample: SampleView = {
        collection_id: 'frame-collection-1',
        sample_id: 'frame-1',
        created_at: new Date(0),
        updated_at: new Date(0)
    };

    const mockVideoData: VideoView = {
        sample_id: 'video-1',
        file_name: 'test.mp4',
        width: 1920,
        height: 1080,
        duration_s: 10,
        fps: 30,
        frame: {
            sample_id: 'frame-1',
            frame_number: 0,
            frame_timestamp_s: 0,
            sample: mockFrameSample
        },
        sample: mockSample
    } as VideoView;

    const mockCurrentFrame = {
        sample_id: 'frame-1',
        frame_number: 5,
        frame_timestamp_s: 0.167,
        sample: mockFrameSample
    };

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should not render when currentFrame is undefined', () => {
        vi.mocked(useVideoFramesModule.useVideoFrames).mockReturnValue({
            currentFrame: writable(undefined),
            loading: false,
            reachedEnd: false,
            playbackTime: writable(0),
            loadFramesFromFrameNumber: vi.fn(),
            loadFrameByPlaybackTime: vi.fn().mockResolvedValue(undefined)
        });

        const { container } = render(VideoFrameDetails, {
            props: { videoData: mockVideoData, datasetId: 'dataset-1', playbackTime: 0 }
        });

        const segment = container.querySelector('[data-testid="current-frame-number"]');
        expect(segment).toBeFalsy();
    });

    it('should render current frame information when frame is available', () => {
        vi.mocked(useVideoFramesModule.useVideoFrames).mockReturnValue({
            currentFrame: writable(mockCurrentFrame),
            loading: false,
            reachedEnd: false,
            playbackTime: writable(0.167),
            loadFramesFromFrameNumber: vi.fn(),
            loadFrameByPlaybackTime: vi.fn().mockResolvedValue(undefined)
        });

        const { getByTestId } = render(VideoFrameDetails, {
            props: { videoData: mockVideoData, datasetId: 'dataset-1', playbackTime: 0 }
        });

        const frameNumber = getByTestId('current-frame-number');
        const frameTimestamp = getByTestId('current-frame-timestamp');

        expect(frameNumber.textContent).toBe('5');
        expect(frameTimestamp.textContent).toBe('0.167 s');
    });

    it('should render view frame button with correct link', () => {
        vi.mocked(useVideoFramesModule.useVideoFrames).mockReturnValue({
            currentFrame: writable(mockCurrentFrame),
            loading: false,
            reachedEnd: false,
            playbackTime: writable(0.167),
            loadFramesFromFrameNumber: vi.fn(),
            loadFrameByPlaybackTime: vi.fn().mockResolvedValue(undefined)
        });

        const { getByTestId } = render(VideoFrameDetails, {
            props: { videoData: mockVideoData, datasetId: 'dataset-1', playbackTime: 0 }
        });

        const viewButton = getByTestId('view-frame-button') as HTMLAnchorElement;
        expect(viewButton).toBeTruthy();
        expect(viewButton.href).toContain('frame-collection-1');
        expect(viewButton.href).toContain('frame-1');
    });

    it('should call loadFramesFromFrameNumber on mount when frameNumber is provided', async () => {
        const loadFramesFromFrameNumber = vi.fn().mockResolvedValue(undefined);

        vi.mocked(useVideoFramesModule.useVideoFrames).mockReturnValue({
            currentFrame: writable(undefined),
            loading: false,
            reachedEnd: false,
            playbackTime: writable(0),
            loadFramesFromFrameNumber,
            loadFrameByPlaybackTime: vi.fn().mockResolvedValue(undefined)
        });

        render(VideoFrameDetails, {
            props: {
                videoData: mockVideoData,
                datasetId: 'dataset-1',
                frameNumber: 5,
                playbackTime: 0
            }
        });

        // Wait for onMount
        await new Promise((resolve) => setTimeout(resolve, 0));

        expect(loadFramesFromFrameNumber).toHaveBeenCalledWith(5);
    });

    it('should call loadFrameByPlaybackTime on mount when playbackTime is provided', async () => {
        const loadFrameByPlaybackTime = vi.fn().mockResolvedValue(undefined);

        vi.mocked(useVideoFramesModule.useVideoFrames).mockReturnValue({
            currentFrame: writable(undefined),
            loading: false,
            reachedEnd: false,
            playbackTime: writable(0),
            loadFramesFromFrameNumber: vi.fn(),
            loadFrameByPlaybackTime
        });

        render(VideoFrameDetails, {
            props: { videoData: mockVideoData, datasetId: 'dataset-1', playbackTime: 0.5 }
        });

        await new Promise((resolve) => setTimeout(resolve, 0));

        expect(loadFrameByPlaybackTime).toHaveBeenCalledWith(0.5, 30);
    });

    it('should handle loadFrameByPlaybackTime errors gracefully', async () => {
        const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
        const loadFrameByPlaybackTime = vi.fn().mockRejectedValue(new Error('Frame not found'));

        vi.mocked(useVideoFramesModule.useVideoFrames).mockReturnValue({
            currentFrame: writable(undefined),
            loading: false,
            reachedEnd: false,
            playbackTime: writable(0),
            loadFramesFromFrameNumber: vi.fn(),
            loadFrameByPlaybackTime
        });

        render(VideoFrameDetails, {
            props: { videoData: mockVideoData, datasetId: 'dataset-1', playbackTime: 0.5 }
        });

        await new Promise((resolve) => setTimeout(resolve, 10));

        expect(consoleErrorSpy).toHaveBeenCalledWith(
            'Failed to load frame by playback time:',
            expect.any(Error)
        );

        consoleErrorSpy.mockRestore();
    });

    it('should sync playbackTime when loading by frameNumber', async () => {
        const hookPlaybackTime = writable(0);

        vi.mocked(useVideoFramesModule.useVideoFrames).mockReturnValue({
            currentFrame: writable(mockCurrentFrame),
            loading: false,
            reachedEnd: false,
            playbackTime: hookPlaybackTime,
            loadFramesFromFrameNumber: vi.fn().mockResolvedValue(undefined),
            loadFrameByPlaybackTime: vi.fn().mockResolvedValue(undefined)
        });

        render(VideoFrameDetails, {
            props: { videoData: mockVideoData, datasetId: 'dataset-1', frameNumber: 5 }
        });

        hookPlaybackTime.set(0.169);
        await new Promise((resolve) => setTimeout(resolve, 10));

        expect(get(hookPlaybackTime)).toBe(0.169);
    });

    it('should sync frameNumber when loading by playbackTime', async () => {
        const hookCurrentFrame = writable<typeof mockCurrentFrame | undefined>(undefined);

        vi.mocked(useVideoFramesModule.useVideoFrames).mockReturnValue({
            currentFrame: hookCurrentFrame,
            loading: false,
            reachedEnd: false,
            playbackTime: writable(0.5),
            loadFramesFromFrameNumber: vi.fn().mockResolvedValue(undefined),
            loadFrameByPlaybackTime: vi.fn().mockResolvedValue(undefined)
        });

        render(VideoFrameDetails, {
            props: { videoData: mockVideoData, datasetId: 'dataset-1', playbackTime: 0.5 }
        });

        hookCurrentFrame.set(mockCurrentFrame);
        await new Promise((resolve) => setTimeout(resolve, 10));

        expect(get(hookCurrentFrame)?.frame_number).toBe(5);
    });
});
