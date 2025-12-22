import { describe, it, expect } from 'vitest';
import { routes, routeHelpers } from './routes';

describe('routes', () => {
    describe('route definitions', () => {
        it('should generate correct collection routes', () => {
            const testCollectionId = '123';
            expect(routes.collection.samples(testCollectionId)).toBe('/collections/123/samples');
            expect(routes.collection.annotations(testCollectionId)).toBe(
                '/collections/123/annotations'
            );
        });
    });

    describe('routeHelpers', () => {
        const testCollectionId = '123';

        it('should generate correct samples route', () => {
            expect(routeHelpers.toSamples(testCollectionId)).toBe('/collections/123/samples');
        });

        it('should generate correct annotations route', () => {
            expect(routeHelpers.toAnnotations(testCollectionId)).toBe(
                '/collections/123/annotations'
            );
        });

        it('should generate correct sample route', () => {
            const testSampleId = '456';
            const collectionId = '123';
            const sampleIndex = 0;
            expect(
                routeHelpers.toSample({
                    sampleId: testSampleId,
                    collectionId: collectionId,
                    sampleIndex: sampleIndex
                })
            ).toBe(`/collections/${collectionId}/samples/${testSampleId}/${sampleIndex}`);
        });

        it('generates correct sample route without index', () => {
            const testSampleId = '456';
            const collectionId = '123';
            expect(
                routeHelpers.toSample({
                    sampleId: testSampleId,
                    collectionId: collectionId
                })
            ).toBe(`/collections/${collectionId}/samples/${testSampleId}`);
        });

        it('should generate route to annotation details', () => {
            const sampleId = '456';
            const annotationId = '789';
            const collectionId = '123';
            const annotationIndex = 0;
            expect(
                routeHelpers.toSampleWithAnnotation({
                    sampleId,
                    annotationId,
                    collectionId,
                    annotationIndex
                })
            ).toBe(
                `/collections/${collectionId}/annotations/${sampleId}/${annotationId}/${annotationIndex}`
            );
        });
    });
});
