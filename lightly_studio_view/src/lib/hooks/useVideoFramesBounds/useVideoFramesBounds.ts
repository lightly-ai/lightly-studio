import { useSessionStorage } from '$lib/hooks/useSessionStorage/useSessionStorage';
import { get, writable } from 'svelte/store';
import {
    getVideoFramesFieldsBounds,
    type VideoFrameFieldsBoundsView
} from '$lib/api/lightly_studio_local';

const videoFramesBoundsValues = useSessionStorage<VideoFrameFieldsBoundsView | null>(
    'lightlyStudio_video_frames_bounds_values',
    null
);
const videoFramesBounds = useSessionStorage<VideoFrameFieldsBoundsView | null>(
    'lightlyStudio_video_frames_bounds',
    null
);

const isInitialized = writable<boolean>(false);

const initializeVideoFramesBounds = async (collection_id: string) => {
    if (get(isInitialized)) {
        return;
    }

    const { data } = await getVideoFramesFieldsBounds({
        path: {
            video_frame_collection_id: collection_id
        }
    });

    isInitialized.set(true);

    if (!data) return;

    videoFramesBoundsValues.set(data);
    videoFramesBounds.set(data);
};

const updateVideoFramesBounds = (data: VideoFrameFieldsBoundsView) => {
    videoFramesBounds.set(data);
};

const updateVideoFramesBoundsValues = (data: VideoFrameFieldsBoundsView) => {
    videoFramesBoundsValues.set(data);
};

export const useVideoFramesBounds = (collection_id?: string) => {
    if (collection_id) {
        initializeVideoFramesBounds(collection_id);
    }

    return {
        videoFramesBounds,
        videoFramesBoundsValues,
        updateVideoFramesBounds,
        updateVideoFramesBoundsValues
    };
};
