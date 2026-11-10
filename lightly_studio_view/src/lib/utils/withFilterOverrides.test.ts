import { describe, expect, it } from 'vitest';
import type {
    AnnotationsFilter,
    FilterDimensions,
    ImageFilter
} from '$lib/api/lightly_studio_local/types.gen.js';
import { imageDimensionRanges, withFilterOverrides } from './withFilterOverrides';

const REGION = {
    polygon: [
        { x: 0, y: 0 },
        { x: 1, y: 0 },
        { x: 0, y: 1 }
    ]
};
const W: FilterDimensions = { min: 1, max: 2 };
const H: FilterDimensions = { min: 3, max: 4 };
const A = { annotation_label_ids: ['a'] } as AnnotationsFilter;
const A2 = { annotation_label_ids: ['b'] } as AnnotationsFilter;

type Filter = Omit<ImageFilter, 'filter_type'> & { filter_type?: 'image' | 'video' };

describe('withFilterOverrides', () => {
    it('passes through fields absent from overrides', () => {
        const base = {
            filter_type: 'image',
            sample_filter: { embedding_region: REGION, tag_ids: ['t'] }
        } as Filter;
        expect(withFilterOverrides('image', base, {})).toEqual(base);
    });

    it('removes keys overridden with undefined', () => {
        const base = {
            filter_type: 'image',
            width: W,
            height: H,
            sample_filter: {
                annotations_filter: A,
                metadata_filters: [],
                embedding_region: REGION
            }
        } as Filter;
        expect(
            withFilterOverrides('image', base, {
                width: undefined,
                height: undefined,
                sample_filter: { annotations_filter: undefined, metadata_filters: undefined }
            })
        ).toEqual({ filter_type: 'image', sample_filter: { embedding_region: REGION } });
    });

    it('replaces overridden keys', () => {
        const base = { filter_type: 'image', sample_filter: { annotations_filter: A } } as Filter;
        expect(
            withFilterOverrides('image', base, { sample_filter: { annotations_filter: A2 } })
        ).toEqual({ filter_type: 'image', sample_filter: { annotations_filter: A2 } });
    });

    it('returns undefined when only removed fields remain', () => {
        const base = { filter_type: 'image', width: W } as Filter;
        expect(withFilterOverrides('image', base, { width: undefined })).toBeUndefined();
    });

    it('returns undefined for null base and empty overrides', () => {
        expect(withFilterOverrides('image', null, {})).toBeUndefined();
    });

    it('builds from overrides when base is null', () => {
        expect(
            withFilterOverrides<Filter, 'image'>('image', null, {
                width: W,
                sample_filter: { annotations_filter: A }
            })
        ).toEqual({ filter_type: 'image', width: W, sample_filter: { annotations_filter: A } });
    });

    it('keeps an empty array override', () => {
        expect(
            withFilterOverrides<Filter, 'image'>('image', null, {
                sample_filter: { metadata_filters: [] }
            })
        ).toEqual({ filter_type: 'image', sample_filter: { metadata_filters: [] } });
    });

    it('sets the given filter type', () => {
        const base = { width: W } as Filter;
        expect(withFilterOverrides('video', base, {})).toEqual({
            filter_type: 'video',
            width: W
        });
    });

    it('does not mutate base', () => {
        const base = {
            filter_type: 'image',
            width: W,
            sample_filter: { annotations_filter: A }
        } as Filter;
        const copy = structuredClone(base);
        withFilterOverrides('image', base, {
            width: undefined,
            sample_filter: { annotations_filter: undefined }
        });
        expect(base).toEqual(copy);
    });
});

describe('imageDimensionRanges', () => {
    it('returns undefined ranges for null bounds', () => {
        expect(imageDimensionRanges(null)).toEqual({ width: undefined, height: undefined });
    });

    it('maps bounds to ranges', () => {
        expect(
            imageDimensionRanges({ min_width: 10, max_width: 20, min_height: 30, max_height: 40 })
        ).toEqual({ width: { min: 10, max: 20 }, height: { min: 30, max: 40 } });
    });
});
