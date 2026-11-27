import { describe, expect, it } from 'vitest';
import { createAnnotationIdMap } from './annotationIdMap';

describe('createAnnotationIdMap', () => {
    it('resolves an ID without a replacement to itself', () => {
        expect(createAnnotationIdMap().resolve('a')).toBe('a');
    });

    it('resolves an ID through a chain of replacements', () => {
        const annotationIds = createAnnotationIdMap();
        annotationIds.replace('a', 'b');
        annotationIds.replace('b', 'c');

        expect(annotationIds.resolve('a')).toBe('c');
        expect(annotationIds.resolve('b')).toBe('c');
    });
});
