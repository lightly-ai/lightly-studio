import { describe, expect, it } from 'vitest';
import { getAnnotationSourceScope } from './annotationSourceScope';

describe('getAnnotationSourceScope', () => {
    it('returns the selection when it is a strict subset', () => {
        expect(getAnnotationSourceScope(['a'], ['a', 'b'])).toEqual(['a']);
    });

    it('returns undefined when every source is selected', () => {
        expect(getAnnotationSourceScope(['a', 'b'], ['a', 'b'])).toBeUndefined();
    });

    it('returns undefined when nothing is selected', () => {
        expect(getAnnotationSourceScope([], ['a', 'b'])).toBeUndefined();
    });
});
