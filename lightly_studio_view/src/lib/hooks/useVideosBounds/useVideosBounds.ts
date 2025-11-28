import type { DimensionBounds } from '$lib/services/loadDimensionBounds';
import { loadDimensionBounds } from '$lib/services/loadDimensionBounds';
import { useSessionStorage } from '$lib/hooks/useSessionStorage/useSessionStorage';
import { get, writable } from 'svelte/store';
import { getFiedlsBounds, type VideoFieldsBoundsView } from '$lib/api/lightly_studio_local';


const videoBoundsValues = useSessionStorage<VideoFieldsBoundsView | null>('lightlyStudio_video_bounds_values', null);
const videoBounds = useSessionStorage<VideoFieldsBoundsView | null>('lightlyStudio_video_bounds', null);

const isInitialized = writable(false as boolean);

const initializeVideoBounds = async (dataset_id: string) => {
    if (get(isInitialized)) {
        return;
    }

    const { data } = await getFiedlsBounds({
        path: {
            dataset_id
        },
        body: {
            annotations_frames_labels_id: null
        }
    })

    isInitialized.set(true);

    if (!data) return ;

    videoBoundsValues.set(data)
    videoBounds.set(data)

};

const updateVideoBounds = (data: VideoFieldsBoundsView) => {
    videoBounds.set(data)
}

const updateVideoBoundsValues = (data: VideoFieldsBoundsView) => {
    videoBoundsValues.set(data)
}

export const useVideoBounds = (dataset_id?: string) => {
    if (dataset_id) {
        initializeVideoBounds(dataset_id)
    }

    return {
        videoBounds,
        videoBoundsValues,
        updateVideoBounds,
        updateVideoBoundsValues,
    };
};
