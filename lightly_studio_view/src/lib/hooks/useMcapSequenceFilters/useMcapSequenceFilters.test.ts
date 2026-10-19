import { describe, expect, it } from 'vitest';
import { get } from 'svelte/store';
import { buildMcapSequenceFilter, useMcapSequenceFilters } from './useMcapSequenceFilters';

describe('buildMcapSequenceFilter', () => {
    it('returns null without a collection', () => {
        expect(buildMcapSequenceFilter(null)).toBeNull();
    });

    it('puts the plot selection into the sample filter', () => {
        const region = { polygon: [{ x: 0, y: 0 }] };

        expect(
            buildMcapSequenceFilter({
                collection_id: 'collection-1',
                sample_ids: ['sequence-1'],
                embedding_region: region
            })
        ).toEqual({
            filter_type: 'mcap_sequence',
            sample_filter: { sample_ids: ['sequence-1'], embedding_region: region }
        });
    });
});

describe('useMcapSequenceFilters', () => {
    it('resets the region when the collection changes', () => {
        const { mcapSequenceFilter, setCollectionId, updateEmbeddingRegion } =
            useMcapSequenceFilters();

        setCollectionId('collection-1');
        updateEmbeddingRegion({ polygon: [{ x: 0, y: 0 }] });
        expect(get(mcapSequenceFilter)?.sample_filter?.embedding_region).toBeDefined();

        setCollectionId('collection-2');
        expect(get(mcapSequenceFilter)).toEqual({ filter_type: 'mcap_sequence' });
    });
});
