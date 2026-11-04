import { describe, expect, it, vi } from 'vitest';
import { get } from 'svelte/store';

const setAnnotationLabel = vi.fn();

vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({ setAnnotationLabel })
}));

import { useStickyClass } from './useStickyClass';
import { useRecentClasses } from '../useRecentClasses/useRecentClasses';

describe('useStickyClass', () => {
    it('pickClass sets the sticky class, the recent list and the context label', () => {
        const { stickyClasses, pickClass } = useStickyClass();

        pickClass('sticky-1', 'deer');

        expect(get(stickyClasses)['sticky-1']).toBe('deer');
        expect(get(useRecentClasses().recentClasses)['sticky-1']).toEqual(['deer']);
        expect(setAnnotationLabel).toHaveBeenCalledWith('deer');
    });
});
