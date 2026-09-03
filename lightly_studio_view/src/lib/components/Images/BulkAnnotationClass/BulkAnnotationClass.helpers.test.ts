import { describe, expect, it } from 'vitest';
import {
    formatApplyResult,
    resolveAnnotationSource,
    toAnnotationClassOptions
} from './BulkAnnotationClass.helpers';

describe('resolveAnnotationSource', () => {
    it('prefers the remembered source', () => {
        expect(
            resolveAnnotationSource({ lastSource: 'predictions', sourceNames: ['annotation'] })
        ).toBe('predictions');
    });

    it('falls back to the default source, then the first existing one, then the default name', () => {
        expect(
            resolveAnnotationSource({ lastSource: undefined, sourceNames: ['gt', 'annotation'] })
        ).toBe('annotation');
        expect(resolveAnnotationSource({ lastSource: undefined, sourceNames: ['gt'] })).toBe('gt');
        expect(resolveAnnotationSource({ lastSource: undefined, sourceNames: [] })).toBe(
            'annotation'
        );
    });
});

describe('toAnnotationClassOptions', () => {
    it('maps annotation labels to id and name options', () => {
        expect(
            toAnnotationClassOptions([
                { annotation_label_id: 'lbl-1', annotation_label_name: 'dog' },
                { annotation_label_name: 'cat' }
            ])
        ).toEqual([
            { id: 'lbl-1', name: 'dog' },
            { id: 'cat', name: 'cat' }
        ]);
    });
});

describe('formatApplyResult', () => {
    it('names the images that already had the class', () => {
        expect(formatApplyResult({ createdCount: 28, skippedCount: 12 })).toBe(
            'Added to 28 of 40 images; 12 already had this class.'
        );
    });

    it('reports a plain success when nothing was skipped', () => {
        expect(formatApplyResult({ createdCount: 40, skippedCount: 0 })).toBe(
            'Added the class to 40 images.'
        );
        expect(formatApplyResult({ createdCount: 1, skippedCount: 0 })).toBe(
            'Added the class to 1 image.'
        );
    });

    it('reports that nothing changed when every image already had the class', () => {
        expect(formatApplyResult({ createdCount: 0, skippedCount: 5 })).toBe(
            'No images changed; all 5 already had this class.'
        );
    });
});
