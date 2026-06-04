import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { describe, expect, it } from 'vitest';
import {
    UNKNOWN_SOURCE_NAME,
    groupAnnotationsBySource
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
