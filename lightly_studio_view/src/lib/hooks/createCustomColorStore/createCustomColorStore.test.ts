import { get } from 'svelte/store';
import { describe, expect, test } from 'vitest';
import { createCustomColorStore } from './createCustomColorStore';

describe('createCustomColorStore previews', () => {
    test('a preview overrides the saved color', () => {
        const store = createCustomColorStore();
        store.setCustomColor('cat', '#111111', 1);
        store.setPreviewColor('cat', { color: '#222222', alpha: 0.5 }, Symbol());

        expect(store.getCustomColor('cat')).toEqual({ color: '#222222', alpha: 0.5 });
        expect(get(store.customColorsStore).cat.color).toBe('#222222');
    });

    test('a null preview shows the default', () => {
        const store = createCustomColorStore();
        store.setCustomColor('cat', '#111111', 1);
        store.setPreviewColor('cat', null, Symbol());

        expect(store.getCustomColor('cat')).toBeUndefined();
        expect(store.hasCustomColor('cat')).toBe(false);
    });

    test('clearPreviewColor of a stale owner keeps the newer preview', () => {
        const store = createCustomColorStore();
        const first = Symbol();
        store.setPreviewColor('cat', { color: '#222222', alpha: 1 }, first);
        store.setPreviewColor('cat', { color: '#333333', alpha: 1 }, Symbol());
        store.clearPreviewColor('cat', first);

        expect(store.getCustomColor('cat')?.color).toBe('#333333');
    });

    test('clearPreviewColor of the owner restores the saved color', () => {
        const store = createCustomColorStore();
        const owner = Symbol();
        store.setCustomColor('cat', '#111111', 1);
        store.setPreviewColor('cat', { color: '#222222', alpha: 1 }, owner);
        store.clearPreviewColor('cat', owner);

        expect(store.getCustomColor('cat')?.color).toBe('#111111');
    });

    test('replaceSavedColors keeps previews', () => {
        const store = createCustomColorStore();
        store.setPreviewColor('cat', { color: '#222222', alpha: 1 }, Symbol());
        store.replaceSavedColors({ dog: { color: '#444444', alpha: 1 } });

        expect(store.getCustomColor('cat')?.color).toBe('#222222');
        expect(store.getCustomColor('dog')?.color).toBe('#444444');
    });

    test('hasSavedColor ignores previews', () => {
        const store = createCustomColorStore();
        store.setPreviewColor('cat', { color: '#222222', alpha: 1 }, Symbol());
        store.setCustomColor('dog', '#444444', 1);
        store.setPreviewColor('dog', null, Symbol());

        expect(store.hasSavedColor('cat')).toBe(false);
        expect(store.hasSavedColor('dog')).toBe(true);
    });
});
