import { describe, expect, it } from 'vitest';
import { get } from 'svelte/store';
import { useVideoFilters } from '$lib/hooks';
import type {
    AnnotationsFilter,
    QueryExpr,
    VideoFieldsBoundsView,
    VideoFilter
} from '$lib/api/lightly_studio_local';
import { buildVideoAnnotationCountsFilter } from './videoAnnotationCountsFilter';

const region = {
    polygon: [
        { x: 0, y: 0 },
        { x: 1, y: 0 },
        { x: 0, y: 1 }
    ]
};
const annotationsFilter = {
    filter_type: 'annotations',
    annotation_label_ids: ['a']
} as AnnotationsFilter;
const metadataFilter = { key: 'k', op: '==', value: 1 } as never;
const videoBounds: VideoFieldsBoundsView = {
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
    it('keeps annotation counts in sync when the video query is applied and cleared', () => {
        const { videoFilter, updateFilterParams, updateQueryExpr } = useVideoFilters();
        const queryExpr: QueryExpr = {
            match_expr: {
                type: 'ordinal_float_expr',
                field: { table: 'video', name: 'duration_s' },
                operator: '>',
                value: 10
            }
        };
        updateFilterParams({ collection_id: 'videos', filters: { tag_ids: ['t'] } });
        updateQueryExpr({ query_expr: queryExpr, query_expr_str: 'duration_s > 10' });
        expect(
            buildVideoAnnotationCountsFilter({ ...defaultParams, videoFilter: get(videoFilter) })
        ).toMatchObject({ sample_filter: { tag_ids: ['t'], query_expr: queryExpr } });

        updateQueryExpr();
        expect(
            buildVideoAnnotationCountsFilter({ ...defaultParams, videoFilter: get(videoFilter) })
        ).toEqual({ filter_type: 'video', sample_filter: { tag_ids: ['t'] } });
    });

    it('passes the plot selection and tags through', () => {
        const videoFilter: VideoFilter = {
            sample_filter: { embedding_region: region, tag_ids: ['t'] }
        };
        expect(buildVideoAnnotationCountsFilter({ ...defaultParams, videoFilter })).toEqual({
            filter_type: 'video',
            sample_filter: { embedding_region: region, tag_ids: ['t'] }
        });
    });

    it('uses the layout bounds, labels and metadata', () => {
        expect(
            buildVideoAnnotationCountsFilter({
                ...defaultParams,
                videoBoundsValues: videoBounds,
                annotationFilter: annotationsFilter,
                metadataFilters: [metadataFilter]
            })
        ).toEqual({
            filter_type: 'video',
            ...videoBounds,
            frame_annotation_filter: annotationsFilter,
            sample_filter: { metadata_filters: [metadataFilter] }
        });
    });

    it('replaces bounds from the video filter', () => {
        const videoFilter: VideoFilter = { fps: { min: 100, max: 200 } };
        expect(
            buildVideoAnnotationCountsFilter({
                ...defaultParams,
                videoFilter,
                videoBoundsValues: videoBounds
            })
        ).toMatchObject({ fps: { min: 5, max: 6 } });
    });

    it('builds from parts when the video filter is null', () => {
        expect(
            buildVideoAnnotationCountsFilter({
                ...defaultParams,
                videoBoundsValues: videoBounds,
                annotationFilter: annotationsFilter
            })
        ).toEqual({
            filter_type: 'video',
            ...videoBounds,
            frame_annotation_filter: annotationsFilter
        });
    });

    it('keeps empty metadata filters', () => {
        expect(buildVideoAnnotationCountsFilter({ ...defaultParams, metadataFilters: [] })).toEqual(
            {
                filter_type: 'video',
                sample_filter: { metadata_filters: [] }
            }
        );
    });
});
