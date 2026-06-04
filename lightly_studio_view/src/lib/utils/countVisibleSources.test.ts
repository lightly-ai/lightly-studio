import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { describe, expect, it } from 'vitest';
import { countVisibleSources } from './countVisibleSources';

const createAnnotation = (sampleId: string, sourceId: string): AnnotationView =>
    ({
        parent_sample_id: 'parent-sample-1',
        sample_id: sampleId,
        annotation_collection_id: sourceId,
        annotation_type: 'object_detection',
        annotation_label: { annotation_label_name: 'cat' },
        created_at: new Date('1970-01-01T00:00:00.000Z'),
        object_detection_details: { x: 0, y: 0, width: 10, height: 10 }
    }) satisfies AnnotationView;

describe('countVisibleSources', () => {
    const annotations = [
        createAnnotation('gt-1', 'source-gt'),
        createAnnotation('gt-2', 'source-gt'),
        createAnnotation('pred-1', 'source-pred')
    ];

    it('counts the distinct sources when nothing is hidden', () => {
        expect(countVisibleSources(annotations, new Set())).toBe(2);
    });

    it('does not count a source whose annotations are all hidden', () => {
        expect(countVisibleSources(annotations, new Set(['gt-1', 'gt-2']))).toBe(1);
    });

    it('counts a source while at least one of its annotations is visible', () => {
        expect(countVisibleSources(annotations, new Set(['gt-1']))).toBe(2);
    });

    it('returns 0 when all annotations are hidden', () => {
        expect(countVisibleSources(annotations, new Set(['gt-1', 'gt-2', 'pred-1']))).toBe(0);
    });

    it('returns 0 when there are no annotations', () => {
        expect(countVisibleSources([], new Set())).toBe(0);
    });
});
