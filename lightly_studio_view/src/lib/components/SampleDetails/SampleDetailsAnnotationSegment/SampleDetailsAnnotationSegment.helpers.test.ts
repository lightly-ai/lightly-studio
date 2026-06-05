import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { describe, expect, it } from 'vitest';
import {
    UNKNOWN_SOURCE_NAME,
    areAllAnnotationsHidden,
    computeSeededHiddenIds,
    groupAnnotationsBySource,
    isSourceGroupInitiallyOpen,
    toggleSourceVisibility
} from './SampleDetailsAnnotationSegment.helpers';

const createAnnotation = (sampleId: string, sourceId: string, labelName: string): AnnotationView =>
    ({
        parent_sample_id: 'parent-sample-1',
        sample_id: sampleId,
        annotation_collection_id: sourceId,
        annotation_type: 'object_detection',
        annotation_label: { annotation_label_name: labelName },
        created_at: new Date('1970-01-01T00:00:00.000Z'),
        object_detection_details: { x: 0, y: 0, width: 10, height: 10 }
    }) satisfies AnnotationView;

const groundTruthSource = { collection_id: 'source-gt', name: 'Ground truth' };
const predictionsSource = { collection_id: 'source-pred', name: 'Predictions' };

describe('groupAnnotationsBySource', () => {
    it('buckets annotations under their source in the given source order', () => {
        const annotations = [
            createAnnotation('a1', predictionsSource.collection_id, 'cat'),
            createAnnotation('a2', groundTruthSource.collection_id, 'dog'),
            createAnnotation('a3', predictionsSource.collection_id, 'dog')
        ];

        const groups = groupAnnotationsBySource(annotations, [
            groundTruthSource,
            predictionsSource
        ]);

        expect(groups).toEqual([
            {
                id: groundTruthSource.collection_id,
                name: groundTruthSource.name,
                annotations: [annotations[1]]
            },
            {
                id: predictionsSource.collection_id,
                name: predictionsSource.name,
                annotations: [annotations[0], annotations[2]]
            }
        ]);
    });

    it('preserves the incoming annotation order within each group', () => {
        const annotations = [
            createAnnotation('a1', groundTruthSource.collection_id, 'apple'),
            createAnnotation('a2', groundTruthSource.collection_id, 'banana'),
            createAnnotation('a3', groundTruthSource.collection_id, 'cat')
        ];

        const groups = groupAnnotationsBySource(annotations, [groundTruthSource]);

        expect(groups[0].annotations.map((annotation) => annotation.sample_id)).toEqual([
            'a1',
            'a2',
            'a3'
        ]);
    });

    it('skips sources without annotations', () => {
        const annotations = [createAnnotation('a1', groundTruthSource.collection_id, 'dog')];

        const groups = groupAnnotationsBySource(annotations, [
            groundTruthSource,
            predictionsSource
        ]);

        expect(groups.map((group) => group.id)).toEqual([groundTruthSource.collection_id]);
    });

    it('appends annotations from unknown sources under a fallback group', () => {
        const annotations = [
            createAnnotation('a1', 'source-unknown', 'dog'),
            createAnnotation('a2', groundTruthSource.collection_id, 'cat')
        ];

        const groups = groupAnnotationsBySource(annotations, [groundTruthSource]);

        expect(groups).toEqual([
            {
                id: groundTruthSource.collection_id,
                name: groundTruthSource.name,
                annotations: [annotations[1]]
            },
            {
                id: 'source-unknown',
                name: UNKNOWN_SOURCE_NAME,
                annotations: [annotations[0]]
            }
        ]);
    });

    it('returns no groups when there are no annotations', () => {
        expect(groupAnnotationsBySource([], [groundTruthSource, predictionsSource])).toEqual([]);
    });
});

describe('areAllAnnotationsHidden', () => {
    const annotations = [
        createAnnotation('a1', groundTruthSource.collection_id, 'cat'),
        createAnnotation('a2', groundTruthSource.collection_id, 'dog')
    ];

    it('returns true when every annotation is hidden', () => {
        expect(areAllAnnotationsHidden(annotations, new Set(['a1', 'a2']))).toBe(true);
    });

    it('returns false when at least one annotation is visible', () => {
        expect(areAllAnnotationsHidden(annotations, new Set(['a1']))).toBe(false);
    });

    it('returns false when there are no annotations', () => {
        expect(areAllAnnotationsHidden([], new Set(['a1']))).toBe(false);
    });
});

describe('toggleSourceVisibility', () => {
    const annotations = [
        createAnnotation('gt-1', groundTruthSource.collection_id, 'cat'),
        createAnnotation('gt-2', groundTruthSource.collection_id, 'dog')
    ];

    it('hides all annotations of the source when at least one is visible', () => {
        expect(toggleSourceVisibility(annotations, new Set(['gt-1']))).toEqual(
            new Set(['gt-1', 'gt-2'])
        );
    });

    it('shows all annotations of the source when all are hidden', () => {
        expect(toggleSourceVisibility(annotations, new Set(['gt-1', 'gt-2']))).toEqual(new Set());
    });

    it('does not affect hidden annotations of other sources', () => {
        expect(toggleSourceVisibility(annotations, new Set(['other-1']))).toEqual(
            new Set(['other-1', 'gt-1', 'gt-2'])
        );
    });

    it('does not mutate the given hidden set', () => {
        const hiddenAnnotationIds = new Set(['gt-1']);

        toggleSourceVisibility(annotations, hiddenAnnotationIds);

        expect(hiddenAnnotationIds).toEqual(new Set(['gt-1']));
    });
});

describe('computeSeededHiddenIds', () => {
    const sources = [groundTruthSource, predictionsSource];
    const annotations = [
        createAnnotation('gt-1', groundTruthSource.collection_id, 'cat'),
        createAnnotation('pred-1', predictionsSource.collection_id, 'cat'),
        createAnnotation('pred-2', predictionsSource.collection_id, 'dog')
    ];

    it('hides annotations whose source is not selected', () => {
        const hiddenIds = computeSeededHiddenIds(
            annotations,
            [groundTruthSource.collection_id],
            sources
        );

        expect(hiddenIds).toEqual(new Set(['pred-1', 'pred-2']));
    });

    it('hides nothing when the selection is empty', () => {
        expect(computeSeededHiddenIds(annotations, [], sources)).toEqual(new Set());
    });

    it('hides nothing when all sources are selected', () => {
        const hiddenIds = computeSeededHiddenIds(
            annotations,
            [groundTruthSource.collection_id, predictionsSource.collection_id],
            sources
        );

        expect(hiddenIds).toEqual(new Set());
    });

    it('hides nothing when the selection does not apply to this dataset', () => {
        const hiddenIds = computeSeededHiddenIds(
            annotations,
            ['source-from-another-dataset'],
            sources
        );

        expect(hiddenIds).toEqual(new Set());
    });

    it('hides annotations of an unselected source even when the selected source has no annotations', () => {
        const predictionsOnly = [
            createAnnotation('pred-1', predictionsSource.collection_id, 'cat')
        ];

        const hiddenIds = computeSeededHiddenIds(
            predictionsOnly,
            [groundTruthSource.collection_id],
            sources
        );

        expect(hiddenIds).toEqual(new Set(['pred-1']));
    });
});

describe('isSourceGroupInitiallyOpen', () => {
    const annotations = [
        createAnnotation('a1', groundTruthSource.collection_id, 'cat'),
        createAnnotation('a2', groundTruthSource.collection_id, 'dog')
    ];

    it('is open when not all annotations are seeded hidden', () => {
        expect(isSourceGroupInitiallyOpen(annotations, new Set(['a1']), null)).toBe(true);
    });

    it('is collapsed when every annotation is seeded hidden', () => {
        expect(isSourceGroupInitiallyOpen(annotations, new Set(['a1', 'a2']), null)).toBe(false);
    });

    it('stays open when it holds the just-created annotation despite being seeded hidden', () => {
        expect(isSourceGroupInitiallyOpen(annotations, new Set(['a1', 'a2']), 'a2')).toBe(true);
    });

    it('ignores a just-created annotation that belongs to another group', () => {
        expect(isSourceGroupInitiallyOpen(annotations, new Set(['a1', 'a2']), 'other-1')).toBe(
            false
        );
    });
});
