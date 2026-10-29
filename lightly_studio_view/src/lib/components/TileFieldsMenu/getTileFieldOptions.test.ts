import { describe, expect, it } from 'vitest';
import { filterTileFieldGroups, getTileFieldOptions } from './getTileFieldOptions';

const tags = [
    { tag_id: 't1', name: 'train' },
    { tag_id: 't2', name: 'night_review' }
];
const sources = [
    { id: 's1', name: 'ground_truth' },
    { id: 's2', name: 'model_v1' }
];

const labelsOf = (groups: ReturnType<typeof getTileFieldOptions>) =>
    groups.map((group) => [group.label, group.options.map((option) => option.label)]);

describe('getTileFieldOptions', () => {
    it('groups fields, single tags, single sources, and metadata for the images grid', () => {
        const groups = getTileFieldOptions({
            isAnnotations: false,
            metadataKeys: ['location'],
            tags,
            sources
        });

        expect(labelsOf(groups)).toEqual([
            ['Fields', ['Annotation classes', 'All tags']],
            ['Tags', ['train', 'night_review']],
            ['Annotation sources', ['ground_truth', 'model_v1']],
            ['Metadata', ['location']]
        ]);
        expect(groups[1].options[0].id).toBe('tag:t1');
        expect(groups[2].options[1].id).toBe('source:s2');
        expect(groups[3].options[0].id).toBe('metadata:location');
    });

    it('keeps the generic fields stored before and leaves out empty groups', () => {
        const groups = getTileFieldOptions({
            isAnnotations: true,
            metadataKeys: [],
            tags: [],
            sources: []
        });

        expect(groups).toEqual([
            {
                label: 'Fields',
                options: [
                    { id: 'classes', label: 'Annotation class' },
                    { id: 'tags', label: 'All tags' },
                    { id: 'source', label: 'Annotation source' }
                ]
            }
        ]);
    });
});

describe('filterTileFieldGroups', () => {
    const groups = getTileFieldOptions({
        isAnnotations: false,
        metadataKeys: ['night', 'location'],
        tags,
        sources
    });

    it('keeps options whose name contains the query, in any case, across groups', () => {
        expect(labelsOf(filterTileFieldGroups(groups, ' NIGHT '))).toEqual([
            ['Tags', ['night_review']],
            ['Metadata', ['night']]
        ]);
    });

    it('returns every group for an empty query and none when nothing matches', () => {
        expect(filterTileFieldGroups(groups, '')).toEqual(groups);
        expect(filterTileFieldGroups(groups, 'zebra')).toEqual([]);
    });
});
