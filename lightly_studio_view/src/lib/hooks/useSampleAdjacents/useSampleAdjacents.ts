import { writable, type Writable } from 'svelte/store';
import { readSamples, type ImageView } from '$lib/api/lightly_studio_local';
import { createMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

type SampleAdjacentsParams = {
    dataset_id: string;
    sampleId: string;
    sampleIndex: number;
    tagIds: string[];
    annotationLabelIds: string[];
    min_width?: number;
    max_width?: number;
    min_height?: number;
    max_height?: number;
    textEmbedding?: number[];
    metadataValues?: Record<string, { min: number; max: number }>;
};

export type SampleAdjacents = {
    isLoading: boolean;
    sampleNext?: ImageView;
    samplePrevious?: ImageView;
    error?: string;
};

export const useSampleAdjacents = ({
    dataset_id,
    sampleIndex,
    tagIds,
    annotationLabelIds,
    min_width,
    max_width,
    min_height,
    max_height,
    textEmbedding,
    metadataValues
}: SampleAdjacentsParams): Writable<SampleAdjacents> => {
    // Store for sample adjacents to not block the rendering of the sample page
    const sampleAdjacents = writable<SampleAdjacents>({
        isLoading: false
    });

    // Load prev/next
    const _load = async () => {
        sampleAdjacents.update((state) => ({
            ...state,
            isLoading: true,
            error: undefined
        }));

        try {
            const { data } = await readSamples({
                path: { dataset_id },
                body: {
                    pagination: {
                        offset: sampleIndex < 1 ? 0 : sampleIndex - 1,
                        limit: 3
                    },
                    filters: {
                        annotation_label_ids: annotationLabelIds,
                        tag_ids: tagIds,
                        width: { min: min_width, max: max_width },
                        height: { min: min_height, max: max_height },
                        metadata_filters: metadataValues
                            ? createMetadataFilters(metadataValues)
                            : undefined
                    },
                    text_embedding: textEmbedding
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

            sampleAdjacents.update((state) => ({
                ...state,
                isLoading: false,
                sampleNext,
                samplePrevious,
                error: undefined
            }));
        } catch (error) {
            sampleAdjacents.update((state) => ({
                ...state,
                isLoading: false,
                error: (error as Error).message || 'Failed to load adjacent samples'
            }));
        }
    };

    _load();

    return sampleAdjacents;
};
