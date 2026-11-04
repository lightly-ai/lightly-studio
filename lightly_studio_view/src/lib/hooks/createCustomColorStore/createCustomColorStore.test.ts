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

    test('getSavedColor ignores previews', () => {
        const store = createCustomColorStore();
        store.setCustomColor('cat', '#111111', 1);
        store.setPreviewColor('cat', { color: '#222222', alpha: 1 }, Symbol());
        store.setPreviewColor('dog', { color: '#333333', alpha: 1 }, Symbol());

        expect(store.getCustomColor('cat')?.color).toBe('#222222');
        expect(store.getSavedColor('cat')?.color).toBe('#111111');
        expect(store.getSavedColor('dog')).toBeUndefined();
    });
});

describe('createCustomColorStore saves', () => {
    const red = { color: '#ff0000', alpha: 1 };
    const blue = { color: '#0000ff', alpha: 1 };

    test('setSavedColor ignores an older sequence', () => {
        const store = createCustomColorStore();
        const older = store.beginSave('cat');
        const newer = store.beginSave('cat');

        store.setSavedColor('cat', blue, newer);
        store.setSavedColor('cat', red, older);

        expect(store.getSavedColor('cat')).toEqual(blue);
    });

    test('setSavedColor with undefined deletes the saved color', () => {
        const store = createCustomColorStore();
        store.setCustomColor('cat', '#ff0000', 1);

        store.setSavedColor('cat', undefined, store.beginSave('cat'));

        expect(store.hasSavedColor('cat')).toBe(false);
    });

    test('reset clears saved colors and previews', () => {
        const store = createCustomColorStore();
        store.setCustomColor('cat', '#ff0000', 1);
        store.setPreviewColor('dog', blue, Symbol());

        store.reset();

        expect(get(store.customColorsStore)).toEqual({});
    });

    test('setSavedColor ignores a save begun before reset', () => {
        const store = createCustomColorStore();
        const ticket = store.beginSave('cat');

        store.reset();
        store.setSavedColor('cat', red, ticket);

        expect(store.getSavedColor('cat')).toBeUndefined();
        expect(store.getGeneration()).toBe(ticket.generation + 1);
    });

    test('replaceSavedColors keeps the generation', () => {
        const store = createCustomColorStore();
        const generation = store.getGeneration();

        store.replaceSavedColors({ cat: red });

        expect(store.getGeneration()).toBe(generation);
    });
});

describe('createCustomColorStore', () => {
    test('keeps state independent between instances', () => {
        const first = createCustomColorStore();
        const second = createCustomColorStore();

        first.setCustomColor('cat', '#ff0000', 0.5);

        expect(first.getCustomColor('cat')).toEqual({ color: '#ff0000', alpha: 0.5 });
        expect(get(first.colorVersion)).toBe(1);
        expect(second.getCustomColor('cat')).toBeUndefined();
        expect(get(second.customColorsStore)).toEqual({});
        expect(get(second.colorVersion)).toBe(0);
    });
});
