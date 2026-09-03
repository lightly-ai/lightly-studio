import { describe, expect, it } from 'vitest';
import {
    buildSelectionCountsFilter,
    formatApplyResult,
    resolveAnnotationSource,
    toAnnotationClassOptions,
    toSelectionClassCounts
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

describe('buildSelectionCountsFilter', () => {
    it('scopes the counts to the selected samples and the target source', () => {
        expect(
            buildSelectionCountsFilter({
                sampleIds: ['s-1', 's-2'],
                annotationSourceId: 'src-1'
            })
        ).toEqual({
            sample_filter: {
                annotations_filter: { collection_ids: ['src-1'] },
                sample_ids: ['s-1', 's-2']
            }
        });
    });
});

describe('toSelectionClassCounts', () => {
    it('uses current_count, which respects the filter, not total_count', () => {
        expect(
            toSelectionClassCounts([
                { label_name: 'dog', current_count: 3, total_count: 120 },
                { label_name: 'cat', current_count: 0, total_count: 7 }
            ])
        ).toEqual([
            { className: 'dog', sampleCount: 3 },
            { className: 'cat', sampleCount: 0 }
        ]);
    });

    it('returns nothing when there is no response yet', () => {
        expect(toSelectionClassCounts(undefined)).toEqual([]);
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
    it('names the images that already had the annotation class', () => {
        expect(formatApplyResult({ createdCount: 28, skippedCount: 12 })).toBe(
            'Added to 28 of 40 images; 12 already had this annotation class.'
        );
    });

    it('reports a plain success when nothing was skipped', () => {
        expect(formatApplyResult({ createdCount: 40, skippedCount: 0 })).toBe(
            'Added the annotation class to 40 images.'
        );
        expect(formatApplyResult({ createdCount: 1, skippedCount: 0 })).toBe(
            'Added the annotation class to 1 image.'
        );
    });

    it('reports that nothing changed when every image already had the annotation class', () => {
        expect(formatApplyResult({ createdCount: 0, skippedCount: 5 })).toBe(
            'No images changed; all 5 already had this annotation class.'
        );
    });
});
