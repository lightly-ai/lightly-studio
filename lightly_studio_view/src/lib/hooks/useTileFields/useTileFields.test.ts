import { describe, expect, it } from 'vitest';
import { get } from 'svelte/store';
import { getMetadataKey, metadataTileField, useTileFields } from './useTileFields';

describe('useTileFields', () => {
    it('toggles fields per collection and keeps tick order', () => {
        const { tileFields, toggleTileField, clearTileFields } = useTileFields();

        toggleTileField('a', 'tags');
        toggleTileField('a', 'classes');
        toggleTileField('b', 'classes');
        expect(get(tileFields)).toMatchObject({ a: ['tags', 'classes'], b: ['classes'] });

        toggleTileField('a', 'tags');
        expect(get(tileFields).a).toEqual(['classes']);

        clearTileFields('a');
        expect(get(tileFields).a).toEqual([]);
        expect(get(tileFields).b).toEqual(['classes']);
    });

    it('keeps the choice in session storage', () => {
        const { toggleTileField } = useTileFields();
        toggleTileField('c', 'source');
        expect(JSON.parse(sessionStorage.getItem('tileFields') ?? '{}').c).toEqual(['source']);
    });
});

describe('metadata field ids', () => {
    it('round-trips the metadata key', () => {
        expect(getMetadataKey(metadataTileField('loc:a'))).toBe('loc:a');
        expect(getMetadataKey('tags')).toBeUndefined();
    });
});
