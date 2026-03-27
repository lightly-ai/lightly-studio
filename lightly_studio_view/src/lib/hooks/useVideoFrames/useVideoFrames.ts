import {
    getAllFrames,
    type FrameView,
    type SampleView,
    type VideoView
} from '$lib/api/lightly_studio_local';
import { getFrameBatchCursor } from '$lib/utils/frame';
import { writable } from 'svelte/store';

/** Number of frames to fetch in each batch from the API */
const BATCH_SIZE = 50;

/**
 * Internal state for the useVideoFrames hook.
 */
interface UseVideoFramesState {
    /** All loaded frames for the current video */
    frames: FrameView[];
    /** The currently selected/active frame */
    currentFrame: FrameView | null | undefined;
    /** Current position in the API pagination */
    cursor: number;
    /** Whether a frame fetch is in progress */
    loading: boolean;
    /** Whether all frames have been fetched */
    reachedEnd: boolean;
    /** Whether the initial frame load has completed */
    hasStarted: boolean;
    /** ID of the last loaded video (for change detection) */
    lastVideoId: string | null;
    /** Whether the current operation is seeking to a specific frame number */
    seekFrameNumber: boolean;
    /** Current playback time in seconds */
    playbackTime: number;
    /** Promise for the current frame batch load, if any */
    pendingLoad: Promise<void> | null;
}

/**
 * Custom hook for managing video frame data and playback state.
 *
 * This hook handles:
 * - Fetching video frames in batches from the API
 * - Loading frames by frame number or playback time
 * - Tracking the current frame and playback position
 * - Managing loading state and pagination
 *
 * @param params - Configuration object
 * @param params.video - The video metadata including sample_id and frame collection info
 *
 * @returns An object containing:
 * - `currentFrame`: Svelte store with the currently active frame
 * - `loading`: Boolean indicating if a fetch is in progress
 * - `reachedEnd`: Boolean indicating if all frames have been loaded
 * - `playbackTime`: Current playback time in seconds
 * - `loadFramesFromFrameNumber`: Function to load and seek to a specific frame number
 * - `loadFrameByPlaybackTime`: Function to load the frame at a specific playback time
 *
 * @example
 * ```ts
 * const { currentFrame, loadFramesFromFrameNumber } = useVideoFrames({ videoData });
 * await loadFramesFromFrameNumber(42); // Load and display frame 42
 * ```
 */
export function useVideoFrames({ video }: { video: VideoView }) {
    const currentFrame = writable<FrameView | undefined>(undefined);
    const playbackTime = writable<number>(0);
    const playbackStep = 0.002;

    const state: UseVideoFramesState = {
        frames: [],
        currentFrame: undefined,
        cursor: 0,
        loading: false,
        reachedEnd: false,
        hasStarted: false,
        lastVideoId: null,
        seekFrameNumber: false,
        playbackTime: 0,
        pendingLoad: null
    };

    function setCurrentFrame(frame: FrameView | null | undefined): void {
        const nextFrame = frame ?? undefined;
        if (state.currentFrame?.sample_id === nextFrame?.sample_id) {
            return;
        }

        state.currentFrame = nextFrame;
        currentFrame.set(nextFrame);
    }

    function getFrameByNumber(frameNumber: number): FrameView | null {
        return state.frames.find((frame) => frame.frame_number === frameNumber) ?? null;
    }

    function getLastLoadedFrame(): FrameView | null {
        return state.frames.at(-1) ?? null;
    }

    /**
     * Loads the next batch of frames from the API.
     * Uses cursor-based pagination to fetch frames incrementally.
     * Automatically updates the internal state with merged frame data.
     *
     * @throws Error if the API request fails
     */
    async function loadFrames(): Promise<void> {
        if (state.loading) {
            await state.pendingLoad;
            return;
        }
        if (state.reachedEnd) return;

        const frameCollectionId = (video?.frame?.sample as SampleView)?.collection_id;
        if (!frameCollectionId) {
            return;
        }

        state.loading = true;
        state.pendingLoad = (async () => {
            try {
                const res = await getAllFrames({
                    path: {
                        video_frame_collection_id: frameCollectionId
                    },
                    query: {
                        cursor: state.cursor,
                        limit: BATCH_SIZE
                    },
                    body: {
                        filter: {
                            video_id: video?.sample_id
                        }
                    }
                });

                const newFrames = res?.data?.data ?? [];

                if (newFrames.length === 0) {
                    state.reachedEnd = true;
                    return;
                }

                state.frames = mergeFrames(state.frames, newFrames);
                // Update cursor for next batch: use server-provided nextCursor if available,
                // otherwise increment by BATCH_SIZE for client-side pagination
                const nextCursor = res?.data?.nextCursor;
                state.cursor = nextCursor ?? state.cursor + BATCH_SIZE;
                state.reachedEnd = nextCursor == null;
            } finally {
                state.loading = false;
                state.pendingLoad = null;
            }
        })();

        await state.pendingLoad;
    }

    /**
     * Loads and seeks to a specific frame by its frame number.
     * Calculates the appropriate cursor position and fetches the batch containing the target frame.
     * Updates the current frame and playback time to match the requested frame.
     *
     * @param frameNumber - The zero-indexed frame number to load and display
     * @throws Error if the specified frame is not found after loading
     */
    async function loadFramesFromFrameNumber(frameNumber: number): Promise<void> {
        if (frameNumber !== null && frameNumber !== undefined) {
            state.seekFrameNumber = true;

            // Check if frame is already loaded
            const existingFrame = getFrameByNumber(frameNumber);

            if (existingFrame) {
                // Frame already loaded, just set it as current
                setCurrentFrame(existingFrame);
                playbackTime.set(existingFrame.frame_timestamp_s + playbackStep);
            } else {
                // Frame not loaded yet, fetch it
                state.cursor = getFrameBatchCursor(frameNumber, BATCH_SIZE);
                state.reachedEnd = false; // Reset since we're seeking to a new position

                await loadFrames();

                const frame = getFrameByNumber(frameNumber);

                if (!frame) {
                    throw new Error('Frame not found for the given frame number');
                }
                setCurrentFrame(frame);

                if (frame) {
                    playbackTime.set(frame.frame_timestamp_s + playbackStep);
                }
            }
        }

        state.hasStarted = true;

        // Set lastVideoId after initial load to track future changes
        if (video && state.lastVideoId === null) {
            state.lastVideoId = video.sample_id;
        }
    }

    /**
     * Loads the frame corresponding to a specific playback time.
     * Calculates the frame index from the current time and FPS, then fetches the appropriate batch.
     * Updates the current frame to match the playback position.
     *
     * @param currentTime - Current playback time in seconds
     * @param fps - Frames per second of the video
     * @throws Error if no video data is available or if the frame is not found
     */
    async function loadFrameByPlaybackTime(currentTime: number, fps: number): Promise<void> {
        if (state.seekFrameNumber) {
            state.seekFrameNumber = false;
        }

        if (!video) throw new Error('No video data available');

        const frameIndex = Math.floor(currentTime * fps);
        const existingFrame = getFrameByNumber(frameIndex);

        if (existingFrame) {
            setCurrentFrame(existingFrame);
        } else {
            const lastLoadedFrame = getLastLoadedFrame();
            if (state.reachedEnd && lastLoadedFrame && frameIndex > lastLoadedFrame.frame_number) {
                setCurrentFrame(lastLoadedFrame);
                return;
            }

            state.cursor = getFrameBatchCursor(frameIndex, BATCH_SIZE);
            state.reachedEnd = false; // Reset since we're seeking to a new position

            await loadFrames();

            const frame =
                getFrameByNumber(frameIndex) ?? (state.reachedEnd ? getLastLoadedFrame() : null);

            if (!frame) {
                throw new Error('Frame not found for the given playback time');
            }

            setCurrentFrame(frame);
        }
    }

    /**
     * Merges existing frames with newly fetched frames, avoiding duplicates.
     * Optimizes for sequential batch loading by checking if the last existing frame
     * matches the first new frame. Otherwise, uses a Map to deduplicate by sample_id.
     *
     * @param existingFrames - Previously loaded frames
     * @param newFrames - Newly fetched frames to merge
     * @returns Combined array of frames, sorted by frame_number
     */
    function mergeFrames(existingFrames: FrameView[], newFrames: FrameView[]): FrameView[] {
        if (existingFrames.at(-1)?.frame_number === newFrames[0]?.frame_number) {
            // Skip the duplicate first frame when concatenating
            return [...existingFrames, ...newFrames.slice(1)];
        }

        const frameMap = new Map<string, FrameView>();

        existingFrames.forEach((frame) => frameMap.set(frame.sample_id, frame));
        newFrames.forEach((frame) => frameMap.set(frame.sample_id, frame));

        return Array.from(frameMap.values()).sort((a, b) => a.frame_number - b.frame_number);
    }

    return {
        currentFrame,
        playbackTime,
        get loading() {
            return state.loading;
        },
        get reachedEnd() {
            return state.reachedEnd;
        },
        loadFramesFromFrameNumber,
        loadFrameByPlaybackTime
    };
}
