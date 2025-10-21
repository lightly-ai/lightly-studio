import { describe, it, expect } from 'vitest';
import { routes, routeHelpers } from './routes';

describe('routes', () => {
    describe('route definitions', () => {
        it('should generate correct dataset routes', () => {
            const testDatasetId = '123';
            expect(routes.dataset.samples(testDatasetId)).toBe('/datasets/123/samples');
            expect(routes.dataset.annotations(testDatasetId)).toBe('/datasets/123/annotations');
        });
    });

    describe('routeHelpers', () => {
        const testDatasetId = '123';

        it('should generate correct samples route', () => {
            expect(routeHelpers.toSamples(testDatasetId)).toBe('/datasets/123/samples');
        });

        it('should generate correct annotations route', () => {
            expect(routeHelpers.toAnnotations(testDatasetId)).toBe('/datasets/123/annotations');
        });

        it('should generate correct sample route', () => {
            const testSampleId = '456';
            const datasetId = '123';
            const sampleIndex = 0;
            expect(
                routeHelpers.toSample({
                    sampleId: testSampleId,
                    datasetId: datasetId,
                    sampleIndex: sampleIndex
                })
            ).toBe(`/datasets/${datasetId}/samples/${testSampleId}/${sampleIndex}`);
        });

        it('generates correct sample route without index', () => {
            const testSampleId = '456';
            const datasetId = '123';
            expect(
                routeHelpers.toSample({
                    sampleId: testSampleId,
                    datasetId: datasetId
                })
            ).toBe(`/datasets/${datasetId}/samples/${testSampleId}`);
        });

        it('should generate route to annotation details', () => {
            const sampleId = '456';
            const annotationId = '789';
            const datasetId = '123';
            const annotationIndex = 0;
            expect(
                routeHelpers.toSampleWithAnnotation({
                    sampleId,
                    annotationId,
                    datasetId,
                    annotationIndex
                })
            ).toBe(
                `/datasets/${datasetId}/annotations/${sampleId}/${annotationId}/${annotationIndex}`
            );
        });
    });
});
