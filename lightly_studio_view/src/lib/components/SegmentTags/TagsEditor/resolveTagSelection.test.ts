import { describe, expect, it } from 'vitest';
import type { TagView } from '$lib/services/types';
import { getAddableTags, getAttachedTagNames, resolveTagSelection } from './resolveTagSelection';

const tag = (tag_id: string, name: string): TagView => ({
    tag_id,
    name,
    created_at: new Date(),
    updated_at: new Date()
});

const collectionTags = [tag('t1', 'Occluded'), tag('t2', 'blurry'), tag('t3', 'truncated')];

describe('resolveTagSelection', () => {
    it('leaves out tags that are attached by id or by name in another case', () => {
        const attached = [{ tag_id: 't1', name: 'Occluded' }, { name: 'BLURRY ' }];

        expect(getAddableTags(collectionTags, attached).map((t) => t.name)).toEqual(['truncated']);
    });

    it('ignores a name already on the sample, whatever its case', () => {
        const attachedNames = getAttachedTagNames([{ tag_id: 't1', name: 'Occluded' }]);

        expect(resolveTagSelection(' occluded ', [], attachedNames)).toEqual({
            kind: 'attached'
        });
    });

    it('picks the existing tag of the collection when the name matches in another case', () => {
        expect(resolveTagSelection('TRUNCATED', collectionTags, new Set())).toEqual({
            kind: 'existing',
            tag: collectionTags[2]
        });
    });

    it('creates a new tag with the trimmed name otherwise', () => {
        expect(resolveTagSelection('  parked car ', collectionTags, new Set())).toEqual({
            kind: 'new',
            name: 'parked car'
        });
    });
});
