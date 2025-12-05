import { writable, type Writable } from 'svelte/store';
import {
    getAllFrames,
    type VideoFrameFilter,
    type VideoFrameView
} from '$lib/api/lightly_studio_local';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

type FramesAdjacentsParams = {
    video_frame_dataset_id: string;
    sampleIndex: number;
    filter: VideoFrameFilter;
};

export type FrameAdjacents = {
    isLoading: boolean;
    sampleNext?: VideoFrameView;
    samplePrevious?: VideoFrameView;
    error?: string;
};

export const useFrameAdjacents = ({
    video_frame_dataset_id,
    sampleIndex,
    filter
}: FramesAdjacentsParams): Writable<FrameAdjacents> => {
    // Store for sample adjacents to not block the rendering of the video frames page
    const FrameAdjacents = writable<FrameAdjacents>({
        isLoading: false
    });

    // Load prev/next
    const _load = async () => {
        FrameAdjacents.update((state) => ({
            ...state,
            isLoading: true,
            error: undefined
        }));

        try {
            const { data } = await getAllFrames({
                path: { video_frame_dataset_id },
                query: {
                    cursor: sampleIndex < 1 ? 0 : sampleIndex - 1,
                    limit: 3
                },
                body: {
                    filter
                },
                throwOnError: true
            });

            const { setfilteredSampleCount } = useGlobalStorage();
            setfilteredSampleCount(data?.total_count);

            let sampleNext = undefined;
            const samplePrevious = sampleIndex > 0 ? data.data[0] : undefined;

            if (data.data.length > 2) {
                sampleNext = sampleIndex == 0 ? data.data[1] : data.data[2];
            }

            FrameAdjacents.update((state) => ({
                ...state,
                isLoading: false,
                sampleNext,
                samplePrevious,
                error: undefined
            }));
        } catch (error) {
            FrameAdjacents.update((state) => ({
                ...state,
                isLoading: false,
                error: (error as Error).message || 'Failed to load adjacent frames'
            }));
        }
    };

    _load();

    return FrameAdjacents;
};
