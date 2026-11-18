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

    it('puts the selected workflow states into the sample filter', () => {
        expect(
            buildMcapSequenceFilter({
                collection_id: 'collection-1',
                workflow_states: ['accepted', 'not_in_workflow']
            })
        ).toEqual({
            filter_type: 'mcap_sequence',
            sample_filter: { workflow_states: ['accepted', 'not_in_workflow'] }
        });
    });

    it('leaves out an empty workflow state list', () => {
        expect(
            buildMcapSequenceFilter({ collection_id: 'collection-1', workflow_states: [] })
        ).toEqual({ filter_type: 'mcap_sequence' });
    });
});

describe('useMcapSequenceFilters', () => {
    it('ignores tags and regions until a collection is set', () => {
        const { mcapSequenceFilter, updateEmbeddingRegion, updateTagIds } =
            useMcapSequenceFilters();

        updateTagIds(['tag-1']);
        updateEmbeddingRegion({ polygon: [{ x: 0, y: 0 }] });
        expect(get(mcapSequenceFilter)).toBeNull();
    });

    it('clears the region and resets the tags when the collection changes', () => {
        const { mcapSequenceFilter, setCollectionId, updateEmbeddingRegion, updateTagIds } =
            useMcapSequenceFilters();

        setCollectionId('collection-1');
        updateTagIds(['tag-1']);
        updateEmbeddingRegion({ polygon: [] });
        expect(get(mcapSequenceFilter)?.sample_filter?.tag_ids).toEqual(['tag-1']);
        expect(get(mcapSequenceFilter)?.sample_filter?.embedding_region).toEqual({ polygon: [] });
        updateEmbeddingRegion(null);
        expect(get(mcapSequenceFilter)?.sample_filter).toEqual({ tag_ids: ['tag-1'] });

        setCollectionId('collection-2');
        expect(get(mcapSequenceFilter)).toEqual({ filter_type: 'mcap_sequence' });
    });

    it('updates the workflow states of the current collection', () => {
        const { mcapSequenceFilter, setCollectionId, updateWorkflowStates } =
            useMcapSequenceFilters();

        setCollectionId('collection-3');
        updateWorkflowStates(['in_review']);
        expect(get(mcapSequenceFilter)?.sample_filter).toEqual({ workflow_states: ['in_review'] });

        updateWorkflowStates(undefined);
        expect(get(mcapSequenceFilter)).toEqual({ filter_type: 'mcap_sequence' });
    });
});
