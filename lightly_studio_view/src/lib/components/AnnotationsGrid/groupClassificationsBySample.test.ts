import { describe, expect, it } from 'vitest';
import {
    AnnotationType,
    SampleType,
    type AnnotationWithPayloadView
} from '$lib/api/lightly_studio_local';
import { groupClassificationsBySample } from './groupClassificationsBySample';

describe('groupClassificationsBySample', () => {
    it('returns an empty array for empty input', () => {
        expect(groupClassificationsBySample([])).toEqual([]);
    });

    it('groups a single classification annotation into one tile', () => {
        const annotations: AnnotationWithPayloadView[] = [
            {
                parent_sample_type: SampleType.IMAGE,
                parent_sample_data: {
                    sample_id: 'image-1'
                } as AnnotationWithPayloadView['parent_sample_data'],
                annotation: {
                    parent_sample_id: 'parent-1',
                    sample_id: 'annotation-1',
                    annotation_type: AnnotationType.CLASSIFICATION
                } as AnnotationWithPayloadView['annotation']
            }
        ];

        const tiles = groupClassificationsBySample(annotations);

        expect(tiles).toHaveLength(1);
        expect(tiles[0].sampleId).toBe('parent-1');
        expect(tiles[0].representative).toBe(annotations[0]);
        expect(tiles[0].allAnnotations).toEqual([annotations[0]]);
    });

    it('groups multiple classification annotations for the same sample into one tile', () => {
        const annotations: AnnotationWithPayloadView[] = [
            {
                parent_sample_type: SampleType.IMAGE,
                parent_sample_data: {
                    sample_id: 'image-1'
                } as AnnotationWithPayloadView['parent_sample_data'],
                annotation: {
                    parent_sample_id: 'parent-1',
                    sample_id: 'annotation-1',
                    annotation_type: AnnotationType.CLASSIFICATION
                } as AnnotationWithPayloadView['annotation']
            },
            {
                parent_sample_type: SampleType.IMAGE,
                parent_sample_data: {
                    sample_id: 'image-1'
                } as AnnotationWithPayloadView['parent_sample_data'],
                annotation: {
                    parent_sample_id: 'parent-1',
                    sample_id: 'annotation-2',
                    annotation_type: AnnotationType.CLASSIFICATION
                } as AnnotationWithPayloadView['annotation']
            },
            {
                parent_sample_type: SampleType.IMAGE,
                parent_sample_data: {
                    sample_id: 'image-1'
                } as AnnotationWithPayloadView['parent_sample_data'],
                annotation: {
                    parent_sample_id: 'parent-1',
                    sample_id: 'annotation-3',
                    annotation_type: AnnotationType.CLASSIFICATION
                } as AnnotationWithPayloadView['annotation']
            }
        ];

        const tiles = groupClassificationsBySample(annotations);

        expect(tiles).toHaveLength(1);
        expect(tiles[0].representative).toBe(annotations[0]);
        expect(tiles[0].allAnnotations).toEqual(annotations);
    });

    it('preserves the order of first occurrence across multiple samples', () => {
        const annotations: AnnotationWithPayloadView[] = [
            {
                parent_sample_type: SampleType.IMAGE,
                parent_sample_data: {
                    sample_id: 'image-2'
                } as AnnotationWithPayloadView['parent_sample_data'],
                annotation: {
                    parent_sample_id: 'parent-2',
                    sample_id: 'annotation-2a',
                    annotation_type: AnnotationType.CLASSIFICATION
                } as AnnotationWithPayloadView['annotation']
            },
            {
                parent_sample_type: SampleType.IMAGE,
                parent_sample_data: {
                    sample_id: 'image-1'
                } as AnnotationWithPayloadView['parent_sample_data'],
                annotation: {
                    parent_sample_id: 'parent-1',
                    sample_id: 'annotation-1a',
                    annotation_type: AnnotationType.CLASSIFICATION
                } as AnnotationWithPayloadView['annotation']
            },
            {
                parent_sample_type: SampleType.IMAGE,
                parent_sample_data: {
                    sample_id: 'image-2'
                } as AnnotationWithPayloadView['parent_sample_data'],
                annotation: {
                    parent_sample_id: 'parent-2',
                    sample_id: 'annotation-2b',
                    annotation_type: AnnotationType.CLASSIFICATION
                } as AnnotationWithPayloadView['annotation']
            },
            {
                parent_sample_type: SampleType.IMAGE,
                parent_sample_data: {
                    sample_id: 'image-1'
                } as AnnotationWithPayloadView['parent_sample_data'],
                annotation: {
                    parent_sample_id: 'parent-1',
                    sample_id: 'annotation-1b',
                    annotation_type: AnnotationType.CLASSIFICATION
                } as AnnotationWithPayloadView['annotation']
            }
        ];

        const tiles = groupClassificationsBySample(annotations);

        expect(tiles).toHaveLength(2);
        expect(tiles.map((tile) => tile.sampleId)).toEqual(['parent-2', 'parent-1']);
        expect(tiles[0].allAnnotations).toEqual([annotations[0], annotations[2]]);
        expect(tiles[1].allAnnotations).toEqual([annotations[1], annotations[3]]);
    });

    it('ignores non-classification annotations when grouping', () => {
        const annotations: AnnotationWithPayloadView[] = [
            {
                parent_sample_type: SampleType.IMAGE,
                parent_sample_data: {
                    sample_id: 'image-1'
                } as AnnotationWithPayloadView['parent_sample_data'],
                annotation: {
                    parent_sample_id: 'parent-1',
                    sample_id: 'annotation-1',
                    annotation_type: AnnotationType.OBJECT_DETECTION
                } as AnnotationWithPayloadView['annotation']
            },
            {
                parent_sample_type: SampleType.IMAGE,
                parent_sample_data: {
                    sample_id: 'image-2'
                } as AnnotationWithPayloadView['parent_sample_data'],
                annotation: {
                    parent_sample_id: 'parent-2',
                    sample_id: 'annotation-2',
                    annotation_type: AnnotationType.CLASSIFICATION
                } as AnnotationWithPayloadView['annotation']
            }
        ];

        const tiles = groupClassificationsBySample(annotations);

        expect(tiles).toHaveLength(1);
        expect(tiles[0].sampleId).toBe('parent-2');
        expect(tiles[0].representative).toBe(annotations[1]);
    });

    it('uses the first annotation seen as the representative for each sample', () => {
        const firstAnnotation: AnnotationWithPayloadView = {
            parent_sample_type: SampleType.IMAGE,
            parent_sample_data: {
                sample_id: 'image-1'
            } as AnnotationWithPayloadView['parent_sample_data'],
            annotation: {
                parent_sample_id: 'parent-1',
                sample_id: 'annotation-1',
                annotation_type: AnnotationType.CLASSIFICATION
            } as AnnotationWithPayloadView['annotation']
        };
        const secondAnnotation: AnnotationWithPayloadView = {
            parent_sample_type: SampleType.IMAGE,
            parent_sample_data: {
                sample_id: 'image-1'
            } as AnnotationWithPayloadView['parent_sample_data'],
            annotation: {
                parent_sample_id: 'parent-1',
                sample_id: 'annotation-2',
                annotation_type: AnnotationType.CLASSIFICATION
            } as AnnotationWithPayloadView['annotation']
        };

        const tiles = groupClassificationsBySample([firstAnnotation, secondAnnotation]);

        expect(tiles[0].representative).toBe(firstAnnotation);
    });
});
