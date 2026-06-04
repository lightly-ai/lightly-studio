import { describe, expect, it } from 'vitest';
import {
    AnnotationType,
    type AnnotationLabel,
    type AnnotationView
} from '$lib/api/lightly_studio_local';
import { getSampleClassificationPills } from './getSampleClassificationPills';

const BASE_ANNOTATION_FIELDS = {
    parent_sample_id: 'parent-sample-id',
    sample_id: 'sample-id',
    created_at: new Date('1970-01-01T00:00:00.000Z')
} satisfies Pick<AnnotationView, 'parent_sample_id' | 'sample_id' | 'created_at'>;

function createAnnotationLabel(annotationLabelName: string): AnnotationLabel {
    return {
        annotation_label_name: annotationLabelName
    } as AnnotationLabel;
}

interface CreateAnnotationParams {
    annotationCollectionId: string;
    annotationLabelName: string;
    annotationType?: AnnotationType;
}

function createAnnotation({
    annotationCollectionId,
    annotationLabelName,
    annotationType = AnnotationType.CLASSIFICATION
}: CreateAnnotationParams): AnnotationView {
    return {
        ...BASE_ANNOTATION_FIELDS,
        annotation_collection_id: annotationCollectionId,
        annotation_type: annotationType,
        annotation_label: createAnnotationLabel(annotationLabelName)
    };
}

describe('getSampleClassificationPills', () => {
    it('returns only visible classification annotations', () => {
        const pills = getSampleClassificationPills({
            annotations: [
                createAnnotation({
                    annotationCollectionId: 'collection-1',
                    annotationLabelName: 'zebra'
                }),
                createAnnotation({
                    annotationCollectionId: 'collection-2',
                    annotationLabelName: 'antelope'
                }),
                createAnnotation({
                    annotationCollectionId: 'collection-1',
                    annotationLabelName: 'ignore-me',
                    annotationType: AnnotationType.OBJECT_DETECTION
                })
            ],
            selectedCollectionIds: ['collection-1'],
            collectionIdToName: {
                'collection-1': 'Animals',
                'collection-2': 'Vehicles'
            }
        });

        expect(pills).toEqual([
            {
                id: 'zebra',
                label: 'zebra',
                displayLabel: 'zebra',
                colorKey: 'zebra',
                title: 'zebra'
            }
        ]);
    });

    it('dedupes identical visible labels across collections when source colors are off', () => {
        const pills = getSampleClassificationPills({
            annotations: [
                createAnnotation({
                    annotationCollectionId: 'collection-1',
                    annotationLabelName: 'car'
                }),
                createAnnotation({
                    annotationCollectionId: 'collection-2',
                    annotationLabelName: 'car'
                })
            ],
            selectedCollectionIds: [],
            collectionIdToName: {
                'collection-1': 'Source A',
                'collection-2': 'Source B'
            }
        });

        expect(pills).toEqual([
            {
                id: 'car',
                label: 'car',
                displayLabel: 'car',
                colorKey: 'car',
                title: 'car'
            }
        ]);
    });

    it('keeps source-specific pills when multiple collections are selected', () => {
        const pills = getSampleClassificationPills({
            annotations: [
                createAnnotation({
                    annotationCollectionId: 'collection-2',
                    annotationLabelName: 'car'
                }),
                createAnnotation({
                    annotationCollectionId: 'collection-1',
                    annotationLabelName: 'car'
                })
            ],
            selectedCollectionIds: ['collection-1', 'collection-2'],
            collectionIdToName: {
                'collection-1': 'Source A',
                'collection-2': 'Source B'
            }
        });

        expect(pills).toEqual([
            {
                id: 'collection-1:car',
                label: 'car',
                displayLabel: 'car',
                colorKey: 'Source A',
                title: 'Source A: car'
            },
            {
                id: 'collection-2:car',
                label: 'car',
                displayLabel: 'car',
                colorKey: 'Source B',
                title: 'Source B: car'
            }
        ]);
    });

    it('sorts pills by id', () => {
        const pills = getSampleClassificationPills({
            annotations: [
                createAnnotation({
                    annotationCollectionId: 'collection-b',
                    annotationLabelName: 'zebra'
                }),
                createAnnotation({
                    annotationCollectionId: 'collection-a',
                    annotationLabelName: 'car'
                }),
                createAnnotation({
                    annotationCollectionId: 'collection-a',
                    annotationLabelName: 'apple'
                })
            ],
            selectedCollectionIds: ['collection-b', 'collection-a'],
            collectionIdToName: {
                'collection-a': 'Collection A',
                'collection-b': 'Collection B'
            }
        });

        expect(pills.map((pill) => pill.id)).toEqual([
            'collection-a:apple',
            'collection-a:car',
            'collection-b:zebra'
        ]);
    });

    it('uses a collection-id fallback for source titles when the source name is unknown', () => {
        const pills = getSampleClassificationPills({
            annotations: [
                createAnnotation({
                    annotationCollectionId: 'missing-collection',
                    annotationLabelName: 'person'
                })
            ],
            selectedCollectionIds: ['missing-collection', 'collection-2'],
            collectionIdToName: {
                'collection-2': 'Known Source'
            }
        });

        expect(pills).toEqual([
            {
                id: 'missing-collection:person',
                label: 'person',
                displayLabel: 'person',
                colorKey: 'Collection missing-collection',
                title: 'Collection missing-collection: person'
            }
        ]);
    });

    it('truncates long labels for display', () => {
        const pills = getSampleClassificationPills({
            annotations: [
                createAnnotation({
                    annotationCollectionId: 'collection-1',
                    annotationLabelName: 'hippopotamus'
                })
            ],
            selectedCollectionIds: [],
            collectionIdToName: {}
        });

        expect(pills[0]).toMatchObject({
            label: 'hippopotamus',
            displayLabel: 'hippopo....',
            title: 'hippopotamus'
        });
    });
});
