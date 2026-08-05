import { derived, get, writable } from 'svelte/store';
import { createMetadataFilters } from '../useMetadataFilters/useMetadataFilters';
import type {
    AnnotationsFilter,
    SampleFilter,
    VideoFilter,
    VideoFieldsBoundsView,
    SortFieldExpr
} from '$lib/api/lightly_studio_local/types.gen';
import type { CategoricalMetadataValues } from '$lib/services/types';
import {
    BLUR_SCORE_KEY,
    LIGHTING_SCORE_KEY,
    MIN_CAPTION_SEGMENT_MATCH_SCORE_KEY,
    MOTION_SCORE_KEY
} from '$lib/constants';
import { MATCH_SCORE_LOW_MAX } from '$lib/utils/captionMatchScore/captionMatchScore';
import {
    BLUR_SCORE_LOW_MAX,
    LIGHTING_SCORE_LOW_MAX,
    MOTION_SCORE_LOW_MAX
} from '$lib/utils/videoQuality/videoQuality';

type MetadataValues = Record<string, { min: number; max: number }>;

export type VideoFilterParams = {
    collection_id: string;
    filters?: {
        tag_ids?: string[];
        annotation_frames_label_ids?: string[];
        sample_ids?: string[];
        metadata_values?: MetadataValues;
        categorical_metadata_values?: CategoricalMetadataValues;
        /** When true, keep only videos whose worst caption match is Low. */
        low_caption_match?: boolean;
        /** When true, keep only videos with blur_score below the default threshold. */
        blurry?: boolean;
        /** When true, keep only videos with lighting_score below the default threshold. */
        poor_lighting?: boolean;
        /** When true, keep only videos with motion_score below the default threshold. */
        static_camera?: boolean;
    };
    video_bounds?: VideoFieldsBoundsView | null;
};

export type VideoSortExpr = SortFieldExpr;

const filterParams = writable<VideoFilterParams | null>(null);
const videoSortBy = writable<VideoSortExpr[] | null>(null);

export const buildVideoFilter = ($filterParams: VideoFilterParams | null): VideoFilter | null => {
    if (!$filterParams?.collection_id) {
        return null;
    }

    const filters: VideoFilter = {
        filter_type: 'video'
    };

    // Add video-specific bounds (width, height, fps, duration_s)
    if ($filterParams.video_bounds) {
        const bounds = $filterParams.video_bounds;

        if (bounds.width) {
            filters.width = {
                min: bounds.width.min ?? undefined,
                max: bounds.width.max ?? undefined
            };
        }

        if (bounds.height) {
            filters.height = {
                min: bounds.height.min ?? undefined,
                max: bounds.height.max ?? undefined
            };
        }

        if (bounds.fps) {
            filters.fps = bounds.fps;
        }

        if (bounds.duration_s) {
            filters.duration_s = bounds.duration_s;
        }
    }

    const sampleFilter: SampleFilter = {};

    const sampleIds = $filterParams.filters?.sample_ids;
    if (sampleIds && sampleIds.length > 0) {
        sampleFilter.sample_ids = sampleIds;
    }

    const tagIds = $filterParams.filters?.tag_ids;
    if (tagIds && tagIds.length > 0) {
        sampleFilter.tag_ids = tagIds;
    }

    const metadataFilters = createMetadataFilters(
        $filterParams.filters?.metadata_values ?? {},
        $filterParams.filters?.categorical_metadata_values ?? {}
    );

    if ($filterParams.filters?.low_caption_match) {
        metadataFilters.push({
            key: MIN_CAPTION_SEGMENT_MATCH_SCORE_KEY,
            op: '<',
            value: MATCH_SCORE_LOW_MAX
        });
    }

    if ($filterParams.filters?.blurry) {
        metadataFilters.push({
            key: BLUR_SCORE_KEY,
            op: '<',
            value: BLUR_SCORE_LOW_MAX
        });
    }

    if ($filterParams.filters?.poor_lighting) {
        metadataFilters.push({
            key: LIGHTING_SCORE_KEY,
            op: '<',
            value: LIGHTING_SCORE_LOW_MAX
        });
    }

    if ($filterParams.filters?.static_camera) {
        metadataFilters.push({
            key: MOTION_SCORE_KEY,
            op: '<',
            value: MOTION_SCORE_LOW_MAX
        });
    }

    if (metadataFilters.length > 0) {
        sampleFilter.metadata_filters = metadataFilters;
    }

    if (Object.keys(sampleFilter).length > 0) {
        filters.sample_filter = sampleFilter;
    }
    const annotationFramesLabelIds = $filterParams.filters?.annotation_frames_label_ids;
    if (annotationFramesLabelIds && annotationFramesLabelIds.length > 0) {
        filters.frame_annotation_filter = {
            filter_type: 'annotations',
            annotation_label_ids: annotationFramesLabelIds
        } satisfies AnnotationsFilter;
    }

    return Object.keys(filters).length > 0 ? filters : null;
};

const videoFilter = derived(filterParams, ($filterParams): VideoFilter | null =>
    buildVideoFilter($filterParams)
);

const setQualityShortcut = (
    key: 'blurry' | 'poor_lighting' | 'static_camera',
    enabled: boolean
) => {
    const params = get(filterParams);
    if (!params || !params.collection_id) {
        return;
    }
    filterParams.set({
        ...params,
        filters: {
            ...params.filters,
            [key]: enabled || undefined
        }
    });
};

export const useVideoFilters = () => {
    const updateFilterParams = (params: VideoFilterParams) => {
        filterParams.set(params);
    };

    const updateSampleIds = (sampleIds: string[]) => {
        const params = get(filterParams);
        if (!params || !params.collection_id) {
            return;
        }

        const newParams: VideoFilterParams = {
            ...params,
            filters: {
                ...params.filters,
                sample_ids: sampleIds.length > 0 ? sampleIds : undefined
            }
        };
        filterParams.set(newParams);
    };

    const updateSortBy = (sort: VideoSortExpr[] | null) => {
        videoSortBy.set(sort);
    };

    const setLowCaptionMatch = (enabled: boolean) => {
        const params = get(filterParams);
        if (!params || !params.collection_id) {
            return;
        }
        filterParams.set({
            ...params,
            filters: {
                ...params.filters,
                low_caption_match: enabled || undefined
            }
        });
    };

    return {
        filterParams,
        videoFilter,
        videoSortBy,
        updateFilterParams,
        updateSampleIds,
        updateSortBy,
        setLowCaptionMatch,
        setBlurry: (enabled: boolean) => setQualityShortcut('blurry', enabled),
        setPoorLighting: (enabled: boolean) => setQualityShortcut('poor_lighting', enabled),
        setStaticCamera: (enabled: boolean) => setQualityShortcut('static_camera', enabled)
    };
};
