import { describe, expect, it } from 'vitest';
import { get } from 'svelte/store';
import { buildMcapSequenceFilter, useMcapSequenceFilters } from './useMcapSequenceFilters';

describe('buildMcapSequenceFilter', () => {
    it('returns null without a collection', () => {
        expect(buildMcapSequenceFilter(null)).toBeNull();
    });

    it('puts the selected tags into the sample filter', () => {
        expect(
            buildMcapSequenceFilter({ collection_id: 'collection-1', tag_ids: ['tag-1'] })
        ).toEqual({
            filter_type: 'mcap_sequence',
            sample_filter: { tag_ids: ['tag-1'] }
        });
    });
});

describe('useMcapSequenceFilters', () => {
    it('ignores tags until a collection is set', () => {
        const { mcapSequenceFilter, updateTagIds } = useMcapSequenceFilters();

        updateTagIds(['tag-1']);
        expect(get(mcapSequenceFilter)).toBeNull();
    });

    it('resets the tags when the collection changes', () => {
        const { mcapSequenceFilter, setCollectionId, updateTagIds } = useMcapSequenceFilters();

        setCollectionId('collection-1');
        updateTagIds(['tag-1']);
        expect(get(mcapSequenceFilter)?.sample_filter?.tag_ids).toEqual(['tag-1']);

        setCollectionId('collection-2');
        expect(get(mcapSequenceFilter)).toEqual({ filter_type: 'mcap_sequence' });
    });
});
