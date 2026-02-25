import { describe, it, expect } from 'vitest';
import { routes, routeHelpers } from './routes';

describe('routes', () => {
    describe('route definitions', () => {
        it('should generate correct collection routes', () => {
            const testDatasetId = 'root-123';
            const testCollectionType = 'image';
            const testCollectionId = '123';
            expect(
                routes.collection.samples(testDatasetId, testCollectionType, testCollectionId)
            ).toBe('/datasets/root-123/image/123/samples');
            expect(
                routes.collection.annotations(testDatasetId, testCollectionType, testCollectionId)
            ).toBe('/datasets/root-123/image/123/annotations');
        });
    });

    describe('routeHelpers', () => {
        const testDatasetId = 'root-123';
        const testCollectionType = 'image';
        const testCollectionId = '123';

        it('should generate correct samples route', () => {
            expect(
                routeHelpers.toSamples(testDatasetId, testCollectionType, testCollectionId)
            ).toBe('/datasets/root-123/image/123/samples');
        });

        it('should generate correct annotations route', () => {
            expect(
                routeHelpers.toAnnotations(testDatasetId, testCollectionType, testCollectionId)
            ).toBe('/datasets/root-123/image/123/annotations');
        });

        it('should generate correct sample route', () => {
            const testSampleId = '456';
            expect(
                routeHelpers.toSample({
                    sampleId: testSampleId,
                    datasetId: testDatasetId,
                    collectionType: testCollectionType,
                    collectionId: testCollectionId
                })
            ).toBe(
                `/datasets/${testDatasetId}/${testCollectionType}/${testCollectionId}/samples/${testSampleId}`
            );
        });

        it('should generate route to annotation details', () => {
            const annotationId = '789';
            expect(
                routeHelpers.toSampleWithAnnotation({
                    annotationId,
                    datasetId: testDatasetId,
                    collectionType: testCollectionType,
                    collectionId: testCollectionId
                })
            ).toBe(
                `/datasets/${testDatasetId}/${testCollectionType}/${testCollectionId}/annotations/${annotationId}`
            );
        });
    });
});
