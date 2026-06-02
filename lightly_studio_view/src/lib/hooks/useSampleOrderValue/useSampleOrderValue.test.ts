import { describe, expect, it } from 'vitest';
import type { ImageView, SampleMetadataView } from '$lib/api/lightly_studio_local';
import { SortDirection } from '$lib/api/lightly_studio_local';
import { useSampleOrderValue } from './useSampleOrderValue';

const baseSample = {
    sample_id: 'sample-1',
    file_name: 'sample-1.jpg',
    file_path_abs: '/data/sample-1.jpg',
    width: 640,
    height: 480,
    annotations: [],
    sample: {
        sample_id: 'sample-1',
        created_at: new Date(),
        updated_at: new Date()
    },
    tags: []
} as ImageView;

describe('useSampleOrderValue', () => {
    it('returns numeric image sort value for width', () => {
        const value = useSampleOrderValue({
            sample: baseSample,
            sortExpr: {
                source: 'image',
                field_name: 'width',
                direction: SortDirection.ASC,
                is_numeric: true
            }
        });

        expect(value).toBe(640);
    });

    it('returns undefined for non-numeric image fields', () => {
        const value = useSampleOrderValue({
            sample: baseSample,
            sortExpr: {
                source: 'image',
                field_name: 'file_name',
                direction: SortDirection.ASC,
                is_numeric: false
            }
        });

        expect(value).toBeUndefined();
    });

    it('returns numeric metadata sort value', () => {
        const sample = {
            ...baseSample,
            metadata_dict: {
                data: { score: 0.875 }
            } as SampleMetadataView
        };

        const value = useSampleOrderValue({
            sample,
            sortExpr: {
                source: 'metadata',
                field_name: 'score',
                direction: SortDirection.DESC,
                is_numeric: true
            }
        });

        expect(value).toBe(0.875);
    });

    it('returns undefined for non-numeric metadata sort fields', () => {
        const sample = {
            ...baseSample,
            metadata_dict: {
                data: { category: 'cat' }
            } as SampleMetadataView
        };

        const value = useSampleOrderValue({
            sample,
            sortExpr: {
                source: 'metadata',
                field_name: 'category',
                direction: SortDirection.ASC,
                is_numeric: false
            }
        });

        expect(value).toBeUndefined();
    });
});
