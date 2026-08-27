import { describe, expect, it } from 'vitest';
import {
    buildMetadataDistributionSource,
    selectCategoricalMetadataKeys,
    selectComparisonSampleTags
} from './metadataDistributionSource';
import type { SampleTagMetadataDistributions } from '$lib/hooks/useMetadataDistributionsBySampleTags';

const width = { binEdges: [0, 1, 2], counts: [3, 4] };

const zurich = {
    id: 'zurich',
    kind: 'value' as const,
    value: 'Zurich',
    label: 'Zurich',
    count: 10
};
const bern = { id: 'bern', kind: 'value' as const, value: 'Bern', label: 'Bern', count: 6 };

const tagDistributions: SampleTagMetadataDistributions[] = [
    {
        id: 'tag-a',
        label: 'Reviewed',
        histograms: { width },
        categorical: { city: [bern] }
    }
];

const params = {
    histograms: { width },
    categoricalKeys: ['city'],
    categorical: { city: [zurich] },
    selectedRanges: { width: { min: 0, max: 1 } },
    selectedValues: { city: ['Zurich'] },
    tagDistributions
};

describe('buildMetadataDistributionSource', () => {
    it('returns null when the dataset has no metadata at all', () => {
        expect(
            buildMetadataDistributionSource({
                ...params,
                histograms: {},
                categoricalKeys: []
            })
        ).toBeNull();
    });

    it('keeps the source when only categorical keys exist', () => {
        const source = buildMetadataDistributionSource({ ...params, histograms: {} });
        expect(source?.groups?.map(({ id }) => id)).toEqual(['city']);
    });

    it('renders numeric keys first, each with its tag series and filter range', () => {
        const source = buildMetadataDistributionSource(params);
        expect(source).toMatchObject({
            id: 'metadata',
            valueNoun: 'samples',
            groups: [
                {
                    id: 'width',
                    histogram: width,
                    histogramSeries: [{ id: 'tag-a', label: 'Reviewed', data: width }],
                    selectedRange: { min: 0, max: 1 }
                },
                { id: 'city' }
            ]
        });
    });

    it('carries the comparison tags buckets so their values stay filterable', () => {
        const source = buildMetadataDistributionSource(params);
        expect(source?.groups?.[1].categorical).toMatchObject({
            buckets: [zurich],
            comparisonBuckets: [{ id: 'bern', value: 'Bern' }],
            selectedValues: ['Zurich']
        });
        expect(source?.groups?.[1].comparisonSeries).toMatchObject([
            { id: 'tag-a', data: [{ id: 'bern', label: 'Bern', count: 6 }] }
        ]);
    });

    it('defers the background bars until the filtered request has returned', () => {
        expect(
            buildMetadataDistributionSource(params)?.groups?.[1].categorical?.filteredBuckets
        ).toBeUndefined();
        expect(
            buildMetadataDistributionSource({
                ...params,
                filteredCategorical: { city: [{ ...zurich, count: 4 }] }
            })?.groups?.[1].categorical?.filteredBuckets
        ).toMatchObject([{ id: 'zurich', count: 4 }]);
    });

    it('falls back to empty selections for a key with no filter applied', () => {
        const source = buildMetadataDistributionSource({
            ...params,
            selectedRanges: {},
            selectedValues: {}
        });
        expect(source?.groups?.[0].selectedRange).toBeUndefined();
        expect(source?.groups?.[1].categorical?.selectedValues).toEqual([]);
        expect(source?.groups?.[1].categorical?.buckets).toEqual([zurich]);
    });

    it('surfaces the categorical and comparison request states separately', () => {
        const source = buildMetadataDistributionSource({
            ...params,
            categoricalLoading: true,
            categoricalError: 'values failed',
            comparisonLoading: true,
            comparisonError: 'tags failed'
        });
        expect(source).toMatchObject({ comparisonLoading: true, comparisonError: 'tags failed' });
        expect(source?.groups?.[1].categorical).toMatchObject({
            loading: true,
            error: 'values failed'
        });
    });

    it('reports an unknown key as empty rather than throwing', () => {
        const source = buildMetadataDistributionSource({ ...params, categoricalKeys: ['country'] });
        expect(source?.groups?.[1].categorical?.buckets).toEqual([]);
        expect(source?.groups?.[1].categorical?.comparisonBuckets).toEqual([]);
    });
});

describe('selectCategoricalMetadataKeys', () => {
    it('keeps string and boolean keys and drops numeric ones', () => {
        expect(
            selectCategoricalMetadataKeys([
                { name: 'city', type: 'string' },
                { name: 'width', type: 'float' },
                { name: 'reviewed', type: 'boolean' },
                { name: 'count', type: 'int' }
            ])
        ).toEqual(['city', 'reviewed']);
    });

    it('treats missing metadata info as no keys', () => {
        expect(selectCategoricalMetadataKeys(undefined)).toEqual([]);
    });
});

describe('selectComparisonSampleTags', () => {
    const items = [
        { value: 'tag-a', label: 'Reviewed' },
        { value: 'tag-b', label: 'Priority' }
    ];

    it('keeps the select order rather than the selection order', () => {
        expect(selectComparisonSampleTags(items, ['tag-b', 'tag-a'])).toEqual([
            { id: 'tag-a', label: 'Reviewed' },
            { id: 'tag-b', label: 'Priority' }
        ]);
    });

    it('ignores an id no longer offered', () => {
        expect(selectComparisonSampleTags(items, ['tag-c'])).toEqual([]);
    });
});
