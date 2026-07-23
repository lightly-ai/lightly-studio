import { describe, expect, it } from 'vitest';
import type { MetadataValueCountsView } from '$lib/api/lightly_studio_local';
import {
    getCategoricalMetadataDistributionRequestOptions,
    selectCategoricalDistributions
} from './useCategoricalMetadataDistribution.svelte';

describe('selectCategoricalDistributions', () => {
    it('preserves typed values and keeps semantic buckets distinct from labels', () => {
        const response: Record<string, MetadataValueCountsView> = {
            city: {
                value_counts: [
                    { value: 'Missing', count: 4 },
                    { value: true, count: 2 }
                ],
                missing_count: 3,
                other_count: 1
            }
        };

        expect(selectCategoricalDistributions(response).city).toEqual([
            {
                id: '["value","string","Missing"]',
                kind: 'value',
                value: 'Missing',
                label: 'Missing (value)',
                count: 4
            },
            {
                id: '["value","boolean",true]',
                kind: 'value',
                value: true,
                label: 'true',
                count: 2
            },
            {
                id: '["missing"]',
                kind: 'missing',
                value: null,
                label: 'Missing (no value)',
                count: 3
            },
            { id: '["other"]', kind: 'other', label: 'Other', count: 1 }
        ]);
    });

    it('omits zero semantic buckets and maps an absent response to an empty record', () => {
        expect(
            selectCategoricalDistributions({
                city: { value_counts: [], missing_count: 0, other_count: 0 }
            })
        ).toEqual({ city: [] });
        expect(selectCategoricalDistributions(undefined)).toEqual({});
    });
});

describe('getCategoricalMetadataDistributionRequestOptions', () => {
    it('forwards the active image filter', () => {
        expect(
            getCategoricalMetadataDistributionRequestOptions({
                collectionId: 'collection-id',
                filter: { width: { min: 100 } }
            })
        ).toEqual({
            path: { collection_id: 'collection-id' },
            body: { filters: { width: { min: 100 } } }
        });
    });
});
