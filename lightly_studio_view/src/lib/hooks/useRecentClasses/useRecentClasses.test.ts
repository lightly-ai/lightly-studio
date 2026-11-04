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
});
