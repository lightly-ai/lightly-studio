import type { AnnotationCollectionView } from '$lib/api/lightly_studio_local';
import { describe, expect, it } from 'vitest';
import { findDropSource, getSourceDropMove } from './annotationSourceDrop';

const sources = [
    { collection_id: 'source-gt', name: 'Ground truth' },
    { collection_id: 'source-pred', name: 'Predictions' },
    { collection_id: 'source-new', name: 'Review' }
] as AnnotationCollectionView[];

describe('getSourceDropMove', () => {
    const dragged = { annotationId: 'a1', sourceId: 'source-gt' };

    it('moves the dragged annotation to another source by name', () => {
        expect(getSourceDropMove(dragged, { id: 'source-pred', name: 'Predictions' })).toEqual({
            annotationIds: ['a1'],
            sourceName: 'Predictions'
        });
    });

    it('does nothing on the annotation own source', () => {
        expect(getSourceDropMove(dragged, { id: 'source-gt', name: 'Ground truth' })).toBeNull();
    });

    it('does nothing without a drag or without a known source', () => {
        expect(getSourceDropMove(null, { id: 'source-pred', name: 'Predictions' })).toBeNull();
        expect(getSourceDropMove(dragged, undefined)).toBeNull();
    });
});

describe('findDropSource', () => {
    it('finds a source by ID and returns undefined for an unknown source', () => {
        expect(findDropSource(sources, 'source-pred')).toEqual({
            id: 'source-pred',
            name: 'Predictions'
        });
        expect(findDropSource(sources, 'source-missing')).toBeUndefined();
    });
});
