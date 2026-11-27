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

    it('puts the selected labels into the group annotation filter', () => {
        expect(
            buildMcapSequenceFilter({
                collection_id: 'collection-1',
                annotation_label_ids: ['label-1']
            })
        ).toEqual({
            filter_type: 'mcap_sequence',
            group_annotation_filter: {
                filter_type: 'annotations',
                annotation_label_ids: ['label-1']
            }
        });
    });

    it('omits the group annotation filter without selected labels', () => {
        expect(
            buildMcapSequenceFilter({ collection_id: 'collection-1', annotation_label_ids: [] })
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

    it('resets the selected labels when the collection changes', () => {
        const { mcapSequenceFilter, setCollectionId, updateAnnotationLabelIds } =
            useMcapSequenceFilters();

        setCollectionId('collection-1');
        updateAnnotationLabelIds(['label-1']);
        expect(get(mcapSequenceFilter)?.group_annotation_filter?.annotation_label_ids).toEqual([
            'label-1'
        ]);

        setCollectionId('collection-2');
        expect(get(mcapSequenceFilter)).toEqual({ filter_type: 'mcap_sequence' });
    });
});
