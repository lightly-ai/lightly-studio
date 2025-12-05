import { writable, type Writable } from 'svelte/store';
import { getAllVideos, type VideoFilter, type VideoView } from '$lib/api/lightly_studio_local';
import { useGlobalStorage } from '../useGlobalStorage';

type VideoAdjacentsParams = {
    dataset_id: string;
    sampleIndex: number;
    filter: VideoFilter;
};

export type VideoAdjacents = {
    isLoading: boolean;
    sampleNext?: VideoView;
    samplePrevious?: VideoView;
    error?: string;
};

export const useVideoAdjacents = ({
    dataset_id,
    sampleIndex,
    filter
}: VideoAdjacentsParams): Writable<VideoAdjacents> => {
    // Store for sample adjacents to not block the rendering of the videos page
    const VideoAdjacents = writable<VideoAdjacents>({
        isLoading: false
    });

    // Load prev/next
    const _load = async () => {
        VideoAdjacents.update((state) => ({
            ...state,
            isLoading: true,
            error: undefined
        }));

        try {
            const { data } = await getAllVideos({
                path: { dataset_id },
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
                sampleNext = sampleIndex === 0 ? data.data[1] : data.data[2];
            }

            VideoAdjacents.update((state) => ({
                ...state,
                isLoading: false,
                sampleNext,
                samplePrevious,
                error: undefined
            }));
        } catch (error) {
            VideoAdjacents.update((state) => ({
                ...state,
                isLoading: false,
                error: (error as Error).message || 'Failed to load adjacent videos'
            }));
        }
    };

    _load();

    return VideoAdjacents;
};
