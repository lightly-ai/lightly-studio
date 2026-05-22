import { get, writable } from 'svelte/store';
import { describe, expect, it } from 'vitest';
import { usePlotColorBy } from './usePlotColorBy';

describe('usePlotColorBy', () => {
    it('returns null when no type is selected', () => {
        const { colorBy } = usePlotColorBy({
            selectedColorByType: writable(null),
            tags: writable([])
        });

        expect(get(colorBy)).toBeNull();
    });

    it('returns metadata_field colorBy when metadata type is selected with a key', () => {
        const { colorBy, setSelectedColorByKey } = usePlotColorBy({
            selectedColorByType: writable('metadata'),
            tags: writable([])
        });

        setSelectedColorByKey('split');

        expect(get(colorBy)).toEqual({ type: 'metadata_field', key: 'split' });
    });

    it('returns null when metadata type is selected but key is null', () => {
        const { colorBy } = usePlotColorBy({
            selectedColorByType: writable('metadata'),
            tags: writable([])
        });

        expect(get(colorBy)).toBeNull();
    });

    it('returns tag colorBy with all tag IDs when tags type is selected', () => {
        const { colorBy } = usePlotColorBy({
            selectedColorByType: writable('tags'),
            tags: writable([{ tag_id: 'tag-a' }, { tag_id: 'tag-b' }])
        });

        expect(get(colorBy)).toEqual({ type: 'tag', tag_ids: ['tag-a', 'tag-b'] });
    });

    it('returns tag colorBy with empty tag_ids when no tags exist', () => {
        const { colorBy } = usePlotColorBy({
            selectedColorByType: writable('tags'),
            tags: writable([])
        });

        expect(get(colorBy)).toEqual({ type: 'tag', tag_ids: [] });
    });

    it('reacts to selectedColorByType changes', () => {
        const selectedColorByType = writable<'metadata' | 'tags' | 'annotation_label' | null>(null);
        const { colorBy, setSelectedColorByKey } = usePlotColorBy({
            selectedColorByType,
            tags: writable([{ tag_id: 'tag-a' }])
        });

        setSelectedColorByKey('split');
        expect(get(colorBy)).toBeNull();

        selectedColorByType.set('metadata');
        expect(get(colorBy)).toEqual({ type: 'metadata_field', key: 'split' });

        selectedColorByType.set('tags');
        expect(get(colorBy)).toEqual({ type: 'tag', tag_ids: ['tag-a'] });

        selectedColorByType.set(null);
        expect(get(colorBy)).toBeNull();
    });

    it('reacts to selectedColorByKey changes', () => {
        const { colorBy, setSelectedColorByKey } = usePlotColorBy({
            selectedColorByType: writable('metadata'),
            tags: writable([])
        });

        expect(get(colorBy)).toBeNull();

        setSelectedColorByKey('city');
        expect(get(colorBy)).toEqual({ type: 'metadata_field', key: 'city' });

        setSelectedColorByKey(null);
        expect(get(colorBy)).toBeNull();
    });

    it('exposes selectedColorByKey as a readable', () => {
        const { selectedColorByKey, setSelectedColorByKey } = usePlotColorBy({
            selectedColorByType: writable(null),
            tags: writable([])
        });

        expect(get(selectedColorByKey)).toBeNull();

        setSelectedColorByKey('split');
        expect(get(selectedColorByKey)).toBe('split');
    });

    it('reacts to tags changes', () => {
        const tags = writable<{ tag_id: string }[]>([]);
        const { colorBy } = usePlotColorBy({
            selectedColorByType: writable('tags'),
            tags
        });

        expect(get(colorBy)).toEqual({ type: 'tag', tag_ids: [] });

        tags.set([{ tag_id: 'tag-a' }, { tag_id: 'tag-b' }]);
        expect(get(colorBy)).toEqual({ type: 'tag', tag_ids: ['tag-a', 'tag-b'] });
    });
});
