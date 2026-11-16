import { beforeEach, describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';

let useRecentClasses: typeof import('./useRecentClasses').useRecentClasses;

describe('useRecentClasses', () => {
    // The recent classes live in module state backed by localStorage. Start each test fresh.
    beforeEach(async () => {
        localStorage.clear();
        vi.resetModules();
        ({ useRecentClasses } = await import('./useRecentClasses'));
    });

    it('puts the newest class first', () => {
        const { recentClasses, addRecentClass } = useRecentClasses();

        addRecentClass('col-1', 'deer');
        addRecentClass('col-1', 'bobcat');

        expect(get(recentClasses)['col-1']).toEqual(['bobcat', 'deer']);
    });

    it('keeps other collections as they are', () => {
        const { recentClasses, addRecentClass } = useRecentClasses();
        addRecentClass('col-1', 'deer');
        addRecentClass('col-1', 'bobcat');

        addRecentClass('col-2', 'fox');

        expect(get(recentClasses)).toEqual({ 'col-1': ['bobcat', 'deer'], 'col-2': ['fox'] });
    });

    it('renames a class in place', () => {
        const { recentClasses, addRecentClass, renameRecentClass } = useRecentClasses();
        addRecentClass('col-1', 'deer');
        addRecentClass('col-1', 'fox');
        addRecentClass('col-2', 'deer');

        renameRecentClass('col-1', 'deer', 'roe deer');

        expect(get(recentClasses)).toEqual({ 'col-1': ['fox', 'roe deer'], 'col-2': ['deer'] });
    });

    it('keeps one entry when renaming to a class already in the list', () => {
        const { recentClasses, addRecentClass, renameRecentClass } = useRecentClasses();
        addRecentClass('col-1', 'deer');
        addRecentClass('col-1', 'fox');

        renameRecentClass('col-1', 'deer', 'fox');

        expect(get(recentClasses)['col-1']).toEqual(['fox']);
    });

    it('removes a deleted class', () => {
        const { recentClasses, addRecentClass, removeRecentClass } = useRecentClasses();
        addRecentClass('col-1', 'deer');
        addRecentClass('col-1', 'fox');

        removeRecentClass('col-1', 'deer');

        expect(get(recentClasses)['col-1']).toEqual(['fox']);
    });
});
