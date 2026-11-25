import { describe, expect, it } from 'vitest';
import {
    getDrawerLabel,
    isPanEnabled,
    reuseUnchangedAnnotations
} from './SampleDetailsImageContainer.helpers';
import type { AnnotationView } from '$lib/api/lightly_studio_local';

const params = {
    isDrawing: false,
    isErasing: false,
    blocksPan: false
};

describe('isPanEnabled', () => {
    it('enables panning without an active drawing tool', () => {
        expect(isPanEnabled(params)).toBe(true);
    });

    it('disables panning while drawing or erasing', () => {
        expect(isPanEnabled({ ...params, isDrawing: true })).toBe(false);
        expect(isPanEnabled({ ...params, isErasing: true })).toBe(false);
    });

    it('disables panning for an assisted labeling tool that blocks it', () => {
        expect(isPanEnabled({ ...params, blocksPan: true })).toBe(false);
    });
});

describe('reuseUnchangedAnnotations', () => {
    const box = (sample_id: string, x: number) =>
        ({ sample_id, created_at: new Date(0), object_detection_details: { x } }) as AnnotationView;

    it('keeps unchanged annotations and takes changed or new ones', () => {
        const previous = [box('a', 1), box('b', 1)];
        const next = reuseUnchangedAnnotations(previous, [box('a', 1), box('b', 2), box('c', 1)]);

        expect(next[0]).toBe(previous[0]);
        expect(next[1]).not.toBe(previous[1]);
        expect(next.map((annotation) => annotation.sample_id)).toEqual(['a', 'b', 'c']);
    });
});

describe('getDrawerLabel', () => {
    it('uses the sticky class when nothing is selected', () => {
        expect(
            getDrawerLabel({ isAnnotationSelected: false, contextLabel: 'cat', stickyClass: 'dog' })
        ).toBe('dog');
    });

    it('has no class when nothing is selected and no class is sticky', () => {
        expect(
            getDrawerLabel({
                isAnnotationSelected: false,
                contextLabel: 'cat',
                stickyClass: undefined
            })
        ).toBeNull();
    });

    it('uses the class of the selected annotation', () => {
        expect(
            getDrawerLabel({ isAnnotationSelected: true, contextLabel: 'cat', stickyClass: 'dog' })
        ).toBe('cat');
    });
});
