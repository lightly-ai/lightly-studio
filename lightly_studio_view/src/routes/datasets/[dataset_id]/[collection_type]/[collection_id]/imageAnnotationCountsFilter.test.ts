import { describe, expect, it } from 'vitest';
import type { AnnotationsFilter, ImageFilter } from '$lib/api/lightly_studio_local/types.gen.js';
import { buildImageAnnotationCountsFilter } from './imageAnnotationCountsFilter';

const REGION = {
    polygon: [
        { x: 0, y: 0 },
        { x: 1, y: 0 },
        { x: 0, y: 1 }
    ]
};
const A = { filter_type: 'annotations', annotation_label_ids: ['a'] } as AnnotationsFilter;
const M = { key: 'k', op: '==', value: 1 } as never;

const defaultParams = {
    imageFilter: null as ImageFilter | null,
    isAnnotations: false,
    dimensionsValues: undefined,
    annotationFilter: undefined,
    metadataFilters: undefined
};

describe('buildImageAnnotationCountsFilter', () => {
    it('passes the plot selection through', () => {
        const imageFilter: ImageFilter = {
            sample_filter: { embedding_region: REGION, tag_ids: ['t'] }
        };
        expect(buildImageAnnotationCountsFilter({ ...defaultParams, imageFilter })).toEqual({
            filter_type: 'image',
            sample_filter: { embedding_region: REGION, tag_ids: ['t'] }
        });
    });

    it('ignores the image filter on the annotations route', () => {
        const imageFilter: ImageFilter = {
            sample_filter: { embedding_region: REGION, tag_ids: ['t'] }
        };
        expect(
            buildImageAnnotationCountsFilter({
                ...defaultParams,
                imageFilter,
                isAnnotations: true,
                annotationFilter: A
            })
        ).toEqual({ filter_type: 'image', sample_filter: { annotations_filter: A } });
    });

    it('builds from parts when the image filter is null', () => {
        expect(
            buildImageAnnotationCountsFilter({
                ...defaultParams,
                dimensionsValues: { min_width: 1, max_width: 2, min_height: 3, max_height: 4 },
                annotationFilter: A,
                metadataFilters: [M]
            })
        ).toEqual({
            filter_type: 'image',
            width: { min: 1, max: 2 },
            height: { min: 3, max: 4 },
            sample_filter: { annotations_filter: A, metadata_filters: [M] }
        });
    });

    it('replaces the annotations filter', () => {
        const imageFilter: ImageFilter = {
            sample_filter: {
                annotations_filter: { filter_type: 'annotations', annotation_label_ids: ['l'] }
            }
        };
        const passed = { ...A, collection_ids: ['c'] } as AnnotationsFilter;
        expect(
            buildImageAnnotationCountsFilter({
                ...defaultParams,
                imageFilter,
                annotationFilter: passed
            })
        ).toEqual({ filter_type: 'image', sample_filter: { annotations_filter: passed } });
    });

    it('drops width and height of the image filter when no dimensions are set', () => {
        const imageFilter: ImageFilter = {
            width: { min: 1, max: 2 },
            height: { min: 3, max: 4 },
            sample_filter: { tag_ids: ['t'] }
        };
        expect(buildImageAnnotationCountsFilter({ ...defaultParams, imageFilter })).toEqual({
            filter_type: 'image',
            sample_filter: { tag_ids: ['t'] }
        });
    });
});
