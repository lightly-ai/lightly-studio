import { describe, expect, it } from 'vitest';
import type { MetadataValueCountsView } from '$lib/api/lightly_studio_local';
import {
    getCategoricalMetadataDistributionRequestOptions,
    selectCategoricalDistributions
} from './useCategoricalMetadataDistribution.svelte';

describe('selectCategoricalDistributions', () => {
    it('maps concrete value counts to labelled value buckets', () => {
        const response: Record<string, MetadataValueCountsView> = {
            city: {
                value_counts: [
                    { value: 'Zurich', count: 10 },
                    { value: true, count: 2 }
                ]
            }
        };

        expect(selectCategoricalDistributions(response).city).toEqual([
            {
                id: '["value","string","Zurich"]',
                kind: 'value',
                value: 'Zurich',
                label: 'Zurich',
                count: 10
            },
            { id: '["value","boolean",true]', kind: 'value', value: true, label: 'true', count: 2 }
        ]);
    });

    it('maps __missing__ sentinel to a missing bucket', () => {
        const response: Record<string, MetadataValueCountsView> = {
            city: { value_counts: [{ value: '__missing__', count: 3 }] }
        };

        expect(selectCategoricalDistributions(response).city).toEqual([
            { id: '["missing"]', kind: 'missing', value: null, label: 'Missing', count: 3 }
        ]);
    });

    it('maps __other__ sentinel to an other bucket', () => {
        const response: Record<string, MetadataValueCountsView> = {
            city: { value_counts: [{ value: '__other__', count: 5 }] }
        };

        expect(selectCategoricalDistributions(response).city).toEqual([
            { id: '["other"]', kind: 'other', label: 'Other', count: 5 }
        ]);
    });

    it('disambiguates literal "Missing" and "Other" values when sentinels are also present', () => {
        const response: Record<string, MetadataValueCountsView> = {
            city: {
                value_counts: [
                    { value: 'Missing', count: 4 },
                    { value: 'Other', count: 1 },
                    { value: '__missing__', count: 3 },
                    { value: '__other__', count: 7 }
                ]
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
                id: '["value","string","Other"]',
                kind: 'value',
                value: 'Other',
                label: 'Other (value)',
                count: 1
            },
            {
                id: '["missing"]',
                kind: 'missing',
                value: null,
                label: 'Missing (no value)',
                count: 3
            },
            { id: '["other"]', kind: 'other', label: 'Other (aggregated)', count: 7 }
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
