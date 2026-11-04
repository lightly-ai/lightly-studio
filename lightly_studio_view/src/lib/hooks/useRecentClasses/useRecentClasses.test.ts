import { describe, expect, it } from 'vitest';
import { get } from 'svelte/store';
import { useRecentClasses } from './useRecentClasses';

describe('useRecentClasses', () => {
    it('puts the newest class first', () => {
        const { recentClasses, addRecentClass } = useRecentClasses();

        addRecentClass('rc-1', 'deer');
        addRecentClass('rc-1', 'bobcat');

        expect(get(recentClasses)['rc-1']).toEqual(['bobcat', 'deer']);
    });

    it('keeps other collections as they are', () => {
        const { recentClasses, addRecentClass } = useRecentClasses();
        addRecentClass('rc-2', 'deer');
        addRecentClass('rc-2', 'bobcat');

        addRecentClass('rc-3', 'fox');

        expect(get(recentClasses)['rc-2']).toEqual(['bobcat', 'deer']);
        expect(get(recentClasses)['rc-3']).toEqual(['fox']);
    });

    it('renames a class in place', () => {
        const { recentClasses, addRecentClass, renameRecentClass } = useRecentClasses();
        addRecentClass('rc-4', 'deer');
        addRecentClass('rc-4', 'fox');
        addRecentClass('rc-5', 'deer');

        renameRecentClass('rc-4', 'deer', 'roe deer');

        expect(get(recentClasses)['rc-4']).toEqual(['fox', 'roe deer']);
        expect(get(recentClasses)['rc-5']).toEqual(['deer']);
    });

    it('keeps one entry when renaming to a class already in the list', () => {
        const { recentClasses, addRecentClass, renameRecentClass } = useRecentClasses();
        addRecentClass('rc-6', 'deer');
        addRecentClass('rc-6', 'fox');

        renameRecentClass('rc-6', 'deer', 'fox');

        expect(get(recentClasses)['rc-6']).toEqual(['fox']);
    });

    it('removes a deleted class', () => {
        const { recentClasses, addRecentClass, removeRecentClass } = useRecentClasses();
        addRecentClass('rc-7', 'deer');
        addRecentClass('rc-7', 'fox');

        removeRecentClass('rc-7', 'deer');

        expect(get(recentClasses)['rc-7']).toEqual(['fox']);
    });
});
