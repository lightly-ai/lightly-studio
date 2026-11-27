import { describe, expect, it } from 'vitest';
import type {
    AnnotationsFilter,
    FilterDimensions,
    ImageFilter
} from '$lib/api/lightly_studio_local';
import { withFilterOverrides } from './withFilterOverrides';

const region = {
    polygon: [
        { x: 0, y: 0 },
        { x: 1, y: 0 },
        { x: 0, y: 1 }
    ]
};
const widthRange: FilterDimensions = { min: 1, max: 2 };
const heightRange: FilterDimensions = { min: 3, max: 4 };
const annotationsFilter = { annotation_label_ids: ['a'] } as AnnotationsFilter;
const otherAnnotationsFilter = { annotation_label_ids: ['b'] } as AnnotationsFilter;

type Filter = Omit<ImageFilter, 'filter_type'> & { filter_type?: 'image' | 'video' };

describe('withFilterOverrides', () => {
    it('passes through fields absent from overrides', () => {
        const base = {
            filter_type: 'image',
            sample_filter: { embedding_region: region, tag_ids: ['t'] }
        } as Filter;
        expect(withFilterOverrides('image', base, {})).toEqual(base);
    });

    it('removes keys overridden with undefined', () => {
        const base = {
            filter_type: 'image',
            width: widthRange,
            height: heightRange,
            sample_filter: {
                annotations_filter: annotationsFilter,
                metadata_filters: [],
                embedding_region: region
            }
        } as Filter;
        expect(
            withFilterOverrides('image', base, {
                width: undefined,
                height: undefined,
                sample_filter: { annotations_filter: undefined, metadata_filters: undefined }
            })
        ).toEqual({ filter_type: 'image', sample_filter: { embedding_region: region } });
    });

    it('replaces overridden keys', () => {
        const base = {
            filter_type: 'image',
            sample_filter: { annotations_filter: annotationsFilter }
        } as Filter;
        expect(
            withFilterOverrides('image', base, {
                sample_filter: { annotations_filter: otherAnnotationsFilter }
            })
        ).toEqual({
            filter_type: 'image',
            sample_filter: { annotations_filter: otherAnnotationsFilter }
        });
    });

    it('returns undefined when only removed fields remain', () => {
        const base = { filter_type: 'image', width: widthRange } as Filter;
        expect(withFilterOverrides('image', base, { width: undefined })).toBeUndefined();
    });

    it('returns undefined for null base and empty overrides', () => {
        expect(withFilterOverrides('image', null, {})).toBeUndefined();
    });

    it('builds from overrides when base is null', () => {
        expect(
            withFilterOverrides<Filter, 'image'>('image', null, {
                width: widthRange,
                sample_filter: { annotations_filter: annotationsFilter }
            })
        ).toEqual({
            filter_type: 'image',
            width: widthRange,
            sample_filter: { annotations_filter: annotationsFilter }
        });
    });

    it('keeps an empty array override', () => {
        expect(
            withFilterOverrides<Filter, 'image'>('image', null, {
                sample_filter: { metadata_filters: [] }
            })
        ).toEqual({ filter_type: 'image', sample_filter: { metadata_filters: [] } });
    });

    it('sets the given filter type', () => {
        const base = { width: widthRange } as Filter;
        expect(withFilterOverrides('video', base, {})).toEqual({
            filter_type: 'video',
            width: widthRange
        });
    });

    it('does not mutate base', () => {
        const base = {
            filter_type: 'image',
            width: widthRange,
            sample_filter: { annotations_filter: annotationsFilter }
        } as Filter;
        const copy = structuredClone(base);
        withFilterOverrides('image', base, {
            width: undefined,
            sample_filter: { annotations_filter: undefined }
        });
        expect(base).toEqual(copy);
    });
});
