import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createMetadataFilters } from '$lib/hooks/useMetadataFilters/useMetadataFilters';
import { buildSampleFilter, toMetadataFilters } from './buildSampleFilter';

vi.mock('$lib/hooks/useMetadataFilters/useMetadataFilters', () => ({
    createMetadataFilters: vi.fn(() => [{ key: 'created' }])
}));

const REGION = {
    polygon: [
        { x: 0, y: 0 },
        { x: 1, y: 0 },
        { x: 0, y: 1 }
    ]
};
const CELL = { evaluation_run_id: 'run-1', gt_label: 'car', pred_label: 'truck' };

describe('buildSampleFilter', () => {
    it('returns undefined for no parts', () => {
        expect(buildSampleFilter({})).toBeUndefined();
    });

    it('returns undefined when every list is empty', () => {
        expect(
            buildSampleFilter({
                sample_ids: [],
                tag_ids: [],
                annotation_label_ids: [],
                annotation_collection_ids: [],
                metadata_filters: []
            })
        ).toBeUndefined();
    });

    it('omits the annotations filter for empty lists', () => {
        const result = buildSampleFilter({
            annotation_label_ids: [],
            annotation_collection_ids: [],
            tag_ids: ['t']
        });
        expect(result).toStrictEqual({ tag_ids: ['t'] });
    });

    it('builds the annotations filter from labels and collections', () => {
        expect(
            buildSampleFilter({ annotation_label_ids: ['l'], annotation_collection_ids: ['c'] })
        ).toEqual({
            annotations_filter: {
                filter_type: 'annotations',
                annotation_label_ids: ['l'],
                collection_ids: ['c']
            }
        });
    });

    it('passes the embedding region through unchanged', () => {
        expect(buildSampleFilter({ embedding_region: REGION })?.embedding_region).toBe(REGION);
    });

    it('drops null values', () => {
        expect(
            buildSampleFilter({ embedding_region: null, confusion_cell: null, query_expr: null })
        ).toBeUndefined();
    });

    it('keeps every set part', () => {
        const query_expr = { kind: 'q' } as never;
        const metadata_filters = [{ key: 'k' }] as never;
        expect(
            buildSampleFilter({
                sample_ids: ['s'],
                tag_ids: ['t'],
                annotation_label_ids: ['l'],
                annotation_collection_ids: ['c'],
                embedding_region: REGION,
                confusion_cell: CELL,
                metadata_filters,
                query_expr
            })
        ).toEqual({
            sample_ids: ['s'],
            tag_ids: ['t'],
            annotations_filter: {
                filter_type: 'annotations',
                annotation_label_ids: ['l'],
                collection_ids: ['c']
            },
            embedding_region: REGION,
            confusion_cell: CELL,
            metadata_filters,
            query_expr
        });
    });
});

describe('toMetadataFilters', () => {
    beforeEach(() => {
        vi.mocked(createMetadataFilters).mockClear();
    });

    it('returns undefined without values', () => {
        expect(toMetadataFilters()).toBeUndefined();
        expect(createMetadataFilters).not.toHaveBeenCalled();
    });

    it('calls createMetadataFilters when either is set', () => {
        const a = { min: 1, max: 2 };
        expect(toMetadataFilters({ a })).toEqual([{ key: 'created' }]);
        expect(createMetadataFilters).toHaveBeenLastCalledWith({ a }, {});
        toMetadataFilters(undefined, { b: [] });
        expect(createMetadataFilters).toHaveBeenLastCalledWith({}, { b: [] });
    });
});
