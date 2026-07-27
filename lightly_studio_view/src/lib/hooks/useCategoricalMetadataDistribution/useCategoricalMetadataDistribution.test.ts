import { describe, expect, it } from 'vitest';
import type { MetadataValueCountsView } from '$lib/api/lightly_studio_local';
import {
    getCategoricalMetadataDistributionRequestOptions,
    selectCategoricalDistributions
} from './useCategoricalMetadataDistribution.svelte';

describe('selectCategoricalDistributions', () => {
    it('maps value counts to labelled buckets', () => {
        const response: Record<string, MetadataValueCountsView> = {
            city: {
                value_counts: [
                    { value: 'Missing', count: 4 },
                    { value: true, count: 2 }
                ]
            }
        };

        expect(selectCategoricalDistributions(response).city).toEqual([
            {
                id: '["value","string","Missing"]',
                kind: 'value',
                value: 'Missing',
                label: 'Missing',
                count: 4
            },
            {
                id: '["value","boolean",true]',
                kind: 'value',
                value: true,
                label: 'true',
                count: 2
            }
        ]);
    });

    it('maps an empty value_counts to an empty array and an absent response to an empty record', () => {
        expect(selectCategoricalDistributions({ city: { value_counts: [] } })).toEqual({
            city: []
        });
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
