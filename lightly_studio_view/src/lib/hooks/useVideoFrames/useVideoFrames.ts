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
 * @param params.videoData - The video metadata including sample_id and frame collection info
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
export function useVideoFrames({ videoData }: { videoData: VideoView }) {
    const currentFrame = writable<FrameView | undefined>(undefined);
    const playbackTime = writable<number>(0);

    const state: UseVideoFramesState = {
        frames: [],
        currentFrame: undefined,
        cursor: 0,
        loading: false,
        reachedEnd: false,
        hasStarted: false,
        lastVideoId: null,
        seekFrameNumber: false,
        playbackTime: 0
    };

    /**
     * Loads the next batch of frames from the API.
     * Uses cursor-based pagination to fetch frames incrementally.
     * Automatically updates the internal state with merged frame data.
     *
     * @throws Error if the API request fails
     */
    async function loadFrames(): Promise<void> {
        if (state.loading || state.reachedEnd) return;
        state.loading = true;

        const frameCollectionId = (videoData?.frame?.sample as SampleView)?.collection_id;
        if (!frameCollectionId) {
            state.loading = false;
            return;
        }

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
                        video_id: videoData?.sample_id
                    }
                }
            });

            const newFrames = res?.data?.data ?? [];

            if (newFrames.length === 0) {
                state.reachedEnd = true;
                state.loading = false;
                return;
            }

            state.frames = mergeFrames(state.frames, newFrames);
            state.cursor = res?.data?.nextCursor ?? state.cursor + BATCH_SIZE;
            state.loading = false;
        } catch (error) {
            state.loading = false;
            throw error;
        }
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
            state.cursor = getFrameBatchCursor(frameNumber, BATCH_SIZE);
            state.reachedEnd = false; // Reset since we're seeking to a new position

            await loadFrames();

            const frame = state.frames.find((frame) => frame.frame_number === frameNumber) ?? null;

            if (!frame) {
                throw new Error('Frame not found for the given frame number');
            }
            currentFrame.set(frame);

            if (frame) {
                playbackTime.set(frame.frame_timestamp_s + 0.002);
            }
        }

        state.hasStarted = true;

        // Set lastVideoId after initial load to track future changes
        if (videoData && state.lastVideoId === null) {
            state.lastVideoId = videoData.sample_id;
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

        if (!videoData) throw new Error('No video data available');

        // Estimate the frame index based on current time and video FPS
        const frameIndex = Math.floor(currentTime * fps);

        // Estimate the cursor position for fetching frames around the current frame index
        state.cursor = getFrameBatchCursor(frameIndex, BATCH_SIZE);
        state.reachedEnd = false; // Reset since we're seeking to a new position

        await loadFrames();

        // Find the exact frame
        const frame = state.frames.find((frame) => frame.frame_number === frameIndex) ?? null;

        if (!frame) {
            throw new Error('Frame not found for the given playback time');
        }

        currentFrame.set(frame);
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
