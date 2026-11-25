import { describe, expect, it } from 'vitest';
import type { ImageFilter } from '$lib/api/lightly_studio_local';
import { buildDistributionBaseFilter } from './distributionBaseFilter';

const region = {
    polygon: [
        { x: 0, y: 0 },
        { x: 1, y: 0 },
        { x: 0, y: 1 }
    ]
};

describe('buildDistributionBaseFilter', () => {
    it('passes the plot selection through', () => {
        const result = buildDistributionBaseFilter({
            sample_filter: { embedding_region: region }
        } as ImageFilter);
        expect(result?.sample_filter?.embedding_region).toEqual(region);
    });

    it('keeps tags, sample ids, confusion cell and query', () => {
        const confusionCell = { predicted_label: 'a', ground_truth_label: 'b' };
        const result = buildDistributionBaseFilter({
            sample_filter: {
                tag_ids: ['t1'],
                sample_ids: ['s1'],
                confusion_cell: confusionCell,
                query_expr: { type: 'x' }
            }
        } as unknown as ImageFilter);
        expect(result?.sample_filter).toEqual({
            tag_ids: ['t1'],
            sample_ids: ['s1'],
            confusion_cell: confusionCell,
            query_expr: { type: 'x' }
        });
    });

    it('strips dimensions, labels and metadata', () => {
        const result = buildDistributionBaseFilter({
            width: { min: 1, max: 2 },
            height: { min: 3, max: 4 },
            sample_filter: {
                annotations_filter: { annotation_label_ids: ['a'] },
                metadata_filters: [{ key: 'k', op: '==', value: 1 }]
            }
        } as unknown as ImageFilter);
        expect(result).toBeUndefined();
    });

    it('returns undefined for a null filter', () => {
        expect(buildDistributionBaseFilter(null)).toBeUndefined();
    });
});
