import { describe, expect, it } from 'vitest';
import { get } from 'svelte/store';
import { resolveStickyClass, useStickyClass } from './useStickyClass';
import { useRecentClasses } from '$lib/hooks/useRecentClasses/useRecentClasses';

describe('useStickyClass', () => {
    it('pickClass sets the sticky class and the recent list', () => {
        const { stickyClasses, pickClass } = useStickyClass();

        pickClass('sticky-1', 'deer');

        expect(get(stickyClasses)['sticky-1']).toBe('deer');
        expect(get(useRecentClasses().recentClasses)['sticky-1']).toEqual(['deer']);
    });
});

describe('resolveStickyClass', () => {
    const resolve = (stickyClass: string | undefined, classNames: string[] | undefined) =>
        resolveStickyClass({ collectionId: 'sticky-2', stickyClass, classNames });

    it('uses a stored class that exists, or any while the classes load', () => {
        expect(resolve('deer', ['deer', 'fox'])).toBe('deer');
        expect(resolve('deer', undefined)).toBe('deer');
    });

    it('treats a restored class that was deleted elsewhere as unset', () => {
        expect(resolve('wolf', ['deer'])).toBeUndefined();
    });

    it('keeps a class picked on this page before it exists', () => {
        useStickyClass().pickClass('sticky-2', 'lynx');

        expect(resolve('lynx', ['deer'])).toBe('lynx');
    });
});
