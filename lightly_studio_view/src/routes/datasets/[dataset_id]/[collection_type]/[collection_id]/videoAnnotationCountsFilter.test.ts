import { describe, expect, it } from 'vitest';
import type {
    AnnotationsFilter,
    VideoFieldsBoundsView,
    VideoFilter
} from '$lib/api/lightly_studio_local/types.gen.js';
import { buildVideoAnnotationCountsFilter } from './videoAnnotationCountsFilter';

const REGION = {
    polygon: [
        { x: 0, y: 0 },
        { x: 1, y: 0 },
        { x: 0, y: 1 }
    ]
};
const A = { filter_type: 'annotations', annotation_label_ids: ['a'] } as AnnotationsFilter;
const M = { key: 'k', op: '==', value: 1 } as never;
const BOUNDS: VideoFieldsBoundsView = {
    width: { min: 1, max: 2 },
    height: { min: 3, max: 4 },
    fps: { min: 5, max: 6 },
    duration_s: { min: 7, max: 8 }
};

const defaultParams = {
    videoFilter: null as VideoFilter | null,
    videoBoundsValues: undefined as VideoFieldsBoundsView | undefined,
    annotationFilter: undefined,
    metadataFilters: undefined
};

describe('buildVideoAnnotationCountsFilter', () => {
    it('passes the plot selection and tags through', () => {
        const videoFilter: VideoFilter = {
            sample_filter: { embedding_region: REGION, tag_ids: ['t'] }
        };
        expect(buildVideoAnnotationCountsFilter({ ...defaultParams, videoFilter })).toEqual({
            filter_type: 'video',
            sample_filter: { embedding_region: REGION, tag_ids: ['t'] }
        });
    });

    it('uses the layout bounds, labels and metadata', () => {
        expect(
            buildVideoAnnotationCountsFilter({
                ...defaultParams,
                videoBoundsValues: BOUNDS,
                annotationFilter: A,
                metadataFilters: [M]
            })
        ).toEqual({
            filter_type: 'video',
            ...BOUNDS,
            frame_annotation_filter: A,
            sample_filter: { metadata_filters: [M] }
        });
    });

    it('replaces bounds from the video filter', () => {
        const videoFilter: VideoFilter = { fps: { min: 100, max: 200 } };
        expect(
            buildVideoAnnotationCountsFilter({
                ...defaultParams,
                videoFilter,
                videoBoundsValues: BOUNDS
            })
        ).toMatchObject({ fps: { min: 5, max: 6 } });
    });

    it('builds from parts when the video filter is null', () => {
        expect(
            buildVideoAnnotationCountsFilter({
                ...defaultParams,
                videoBoundsValues: BOUNDS,
                annotationFilter: A
            })
        ).toEqual({ filter_type: 'video', ...BOUNDS, frame_annotation_filter: A });
    });
});
