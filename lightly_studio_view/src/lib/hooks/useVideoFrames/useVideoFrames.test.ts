import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useVideoFrames } from './useVideoFrames';
import type {
    VideoView,
    VideoFrameView,
    SampleView,
    FrameView
} from '$lib/api/lightly_studio_local';
import * as api from '$lib/api/lightly_studio_local';
import { get } from 'svelte/store';

type MockGetAllFramesResponse = Awaited<ReturnType<typeof api.getAllFrames>>;

vi.mock('$lib/api/lightly_studio_local', async () => {
    const actual = await vi.importActual('$lib/api/lightly_studio_local');
    return {
        ...actual,
        getAllFrames: vi.fn()
    };
});

describe('useVideoFrames', () => {
    const mockSample: SampleView = {
        collection_id: 'video-collection-1',
        sample_id: 'video-1',
        created_at: new Date(0),
        updated_at: new Date(0)
    };

    const mockFrameSample1: SampleView = {
        collection_id: 'frame-collection-1',
        sample_id: 'frame-1',
        created_at: new Date(0),
        updated_at: new Date(0)
    };

    const mockFrameSample2: SampleView = {
        collection_id: 'frame-collection-1',
        sample_id: 'frame-2',
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
            sample: mockFrameSample1
        },
        sample: mockSample
    } as VideoView;

    const mockFrames: VideoFrameView[] = [
        {
            sample_id: 'frame-1',
            frame_number: 0,
            frame_timestamp_s: 0,
            sample: mockFrameSample1,
            video: mockVideoData
        },
        {
            sample_id: 'frame-2',
            frame_number: 1,
            frame_timestamp_s: 0.033,
            sample: mockFrameSample2,
            video: mockVideoData
        }
    ];

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should initialize with default values', () => {
        const hook = useVideoFrames({ video: mockVideoData });

        expect(get(hook.currentFrame)).toBeUndefined();
        expect(hook.loading).toBe(false);
        expect(hook.reachedEnd).toBe(false);
        expect(get(hook.playbackTime)).toBe(0);
    });

    it('should load frames and update currentFrame store', async () => {
        vi.mocked(api.getAllFrames).mockResolvedValue({
            data: {
                data: mockFrames,
                total_count: mockFrames.length
            },
            error: undefined
        } as unknown as MockGetAllFramesResponse);

        const hook = useVideoFrames({ video: mockVideoData });

        // Subscribe to currentFrame store to verify reactivity
        const values: (FrameView | undefined)[] = [];
        const unsubscribe = hook.currentFrame.subscribe((value) => {
            values.push(value);
        });

        await hook.loadFramesFromFrameNumber(1);

        expect(api.getAllFrames).toHaveBeenCalledWith({
            path: {
                video_frame_collection_id: 'frame-collection-1'
            },
            body: {
                filter: {
                    video_id: 'video-1'
                }
            }
        });

        expect(hook.loading).toBe(false);
        expect(get(hook.currentFrame)?.frame_number).toBe(1);
        expect(values).toHaveLength(2); // Initial undefined + update

        unsubscribe();
    });

    it('should load frame by playback time and update store', async () => {
        vi.mocked(api.getAllFrames).mockResolvedValue({
            data: {
                data: mockFrames,
                total_count: mockFrames.length
            },
            error: undefined
        } as unknown as MockGetAllFramesResponse);

        const hook = useVideoFrames({ video: mockVideoData });

        // 0.05 * 30 = 1.5, which floors to 1
        await hook.loadFrameByPlaybackTime(0.05, 30);

        const currentFrame = get(hook.currentFrame);
        expect(currentFrame?.frame_number).toBe(1);
        expect(currentFrame?.sample_id).toBe('frame-2');
    });

    it('should not fetch again when frames are already loaded', async () => {
        vi.mocked(api.getAllFrames).mockResolvedValue({
            data: {
                data: mockFrames,
                total_count: mockFrames.length
            },
            error: undefined
        } as unknown as MockGetAllFramesResponse);

        const hook = useVideoFrames({ video: mockVideoData });
        await hook.loadFramesFromFrameNumber(0);

        vi.mocked(api.getAllFrames).mockClear();

        await hook.loadFrameByPlaybackTime(0.05, 30);

        expect(api.getAllFrames).not.toHaveBeenCalled();
        expect(get(hook.currentFrame)?.frame_number).toBe(1);
    });

    it('should load all frames when loadFrames is called directly', async () => {
        vi.mocked(api.getAllFrames).mockResolvedValue({
            data: {
                data: mockFrames,
                total_count: mockFrames.length
            },
            error: undefined
        } as unknown as MockGetAllFramesResponse);

        const hook = useVideoFrames({ video: mockVideoData });

        expect(hook.loading).toBe(false);
        expect(hook.reachedEnd).toBe(false);

        await hook.loadFrames();

        expect(api.getAllFrames).toHaveBeenCalledWith({
            path: {
                video_frame_collection_id: 'frame-collection-1'
            },
            body: {
                filter: {
                    video_id: 'video-1'
                }
            }
        });

        expect(hook.loading).toBe(false);
        expect(hook.reachedEnd).toBe(true);
    });

    it('should not load frames multiple times if already loading', async () => {
        let resolvePromise: (value: MockGetAllFramesResponse) => void;
        const apiPromise = new Promise<MockGetAllFramesResponse>((resolve) => {
            resolvePromise = resolve;
        });

        vi.mocked(api.getAllFrames).mockReturnValue(
            apiPromise as ReturnType<typeof api.getAllFrames>
        );

        const hook = useVideoFrames({ video: mockVideoData });

        // Start loading frames
        const firstLoad = hook.loadFrames();
        expect(hook.loading).toBe(true);

        // Try to load again while first load is in progress
        const secondLoad = hook.loadFrames();

        // Resolve the API call
        resolvePromise!({
            data: {
                data: mockFrames,
                total_count: mockFrames.length
            },
            error: undefined
        } as unknown as MockGetAllFramesResponse);

        // Wait for both to complete
        await Promise.all([firstLoad, secondLoad]);

        // Should only have called the API once
        expect(api.getAllFrames).toHaveBeenCalledTimes(1);
    });

    it('should throw error when frame number is not found', async () => {
        vi.mocked(api.getAllFrames).mockResolvedValue({
            data: {
                data: mockFrames,
                total_count: mockFrames.length
            },
            error: undefined
        } as unknown as MockGetAllFramesResponse);

        const hook = useVideoFrames({ video: mockVideoData });

        await expect(hook.loadFramesFromFrameNumber(100)).rejects.toThrow(
            'Frame not found for the given frame number'
        );
    });

    it('should throw error when video data is not available', async () => {
        const hook = useVideoFrames({ video: null as unknown as VideoView });

        await expect(hook.loadFrameByPlaybackTime(0, 30)).rejects.toThrow(
            'No video data available'
        );
    });

    describe('reactivity', () => {
        it('should notify subscribers when currentFrame changes', async () => {
            vi.mocked(api.getAllFrames).mockResolvedValue({
                data: {
                    data: mockFrames,
                    total_count: mockFrames.length
                },
                error: undefined
            } as unknown as MockGetAllFramesResponse);

            const hook = useVideoFrames({ video: mockVideoData });

            const values: (FrameView | undefined)[] = [];
            const unsubscribe = hook.currentFrame.subscribe((value) => {
                values.push(value);
            });

            await hook.loadFramesFromFrameNumber(0);
            await hook.loadFrameByPlaybackTime(0.05, 30);

            expect(values).toHaveLength(3); // Initial undefined + 2 updates
            expect(values[0]).toBeUndefined();
            expect(values[1]?.frame_number).toBe(0);
            expect(values[2]?.frame_number).toBe(1);

            unsubscribe();
        });

        it('should keep the last frame selected at the end of the video', async () => {
            const finalFrames = [
                {
                    sample_id: 'frame-1',
                    frame_number: 0,
                    frame_timestamp_s: 0,
                    sample: mockFrameSample1,
                    video: mockVideoData
                },
                {
                    sample_id: 'frame-2',
                    frame_number: 29,
                    frame_timestamp_s: 0.9667,
                    sample: mockFrameSample2,
                    video: mockVideoData
                }
            ] as VideoFrameView[];

            vi.mocked(api.getAllFrames).mockResolvedValue({
                data: {
                    data: finalFrames,
                    total_count: finalFrames.length
                },
                error: undefined
            } as unknown as MockGetAllFramesResponse);

            const hook = useVideoFrames({ video: mockVideoData });
            await hook.loadFramesFromFrameNumber(0);

            vi.mocked(api.getAllFrames).mockClear();

            // Request frame 30+ (at 1 second), should get frame 29 (the last one)
            await hook.loadFrameByPlaybackTime(1, 30);

            expect(get(hook.currentFrame)?.frame_number).toBe(29);
        });
    });
});
