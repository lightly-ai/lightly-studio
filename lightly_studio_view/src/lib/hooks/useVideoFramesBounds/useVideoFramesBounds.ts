import { useSessionStorage } from '$lib/hooks/useSessionStorage/useSessionStorage';
import { get, writable } from 'svelte/store';
import {
    getFieldsBounds,
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

const isInitialized = writable(false as boolean);

const initializeVideoFramesBounds = async (dataset_id: string) => {
    if (get(isInitialized)) {
        return;
    }

    const { data } = await getVideoFramesFieldsBounds({
        path: {
            video_frame_dataset_id: dataset_id
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

export const useVideoFramesBounds = (dataset_id?: string) => {
    if (dataset_id) {
        initializeVideoFramesBounds(dataset_id);
    }

    return {
        videoFramesBounds,
        videoFramesBoundsValues,
        updateVideoFramesBounds,
        updateVideoFramesBoundsValues
    };
};
