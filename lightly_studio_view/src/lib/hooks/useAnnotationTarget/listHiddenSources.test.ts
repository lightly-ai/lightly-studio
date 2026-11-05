import { describe, expect, it } from 'vitest';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { listHiddenSources } from './listHiddenSources';

const sources = [
    { collection_id: 's1', name: 'labels' },
    { collection_id: 's2', name: 'predictions' },
    { collection_id: 's3', name: 'empty' }
];
const annotation = (id: string, sourceId: string, type = 'object_detection') =>
    ({
        sample_id: id,
        annotation_collection_id: sourceId,
        annotation_type: type
    }) as AnnotationView;

describe('listHiddenSources', () => {
    it('lists the sources whose annotations are all hidden, never an empty one', () => {
        const annotations = [annotation('a', 's1'), annotation('b', 's1'), annotation('c', 's2')];

        expect(listHiddenSources(sources, annotations, new Set(['a', 'b']))).toEqual(['labels']);
        expect(listHiddenSources(sources, annotations, new Set(['a']))).toEqual([]);
    });

    it('ignores classifications, like the Annotations panel', () => {
        const annotations = [annotation('a', 's1'), annotation('k', 's1', 'classification')];

        expect(listHiddenSources(sources, annotations, new Set(['a']))).toEqual(['labels']);
    });
});
