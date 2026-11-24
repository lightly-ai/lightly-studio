import { describe, it, expect } from 'vitest';
import {
    routes,
    routeHelpers,
    APP_ROUTES,
    isEvaluationCompareRoute,
    isImagesRoute,
    isAnnotationsRoute,
    isVideosRoute,
    isVideoFramesRoute,
    isGroupsRoute,
    isSampleDetailsRoute,
    isAnnotationDetailsRoute,
    isVideoDetailsRoute,
    isFrameDetailsRoute,
    isMcapSequencesRoute,
    isPointCloudLabelingRoute
} from './routes';

describe('routes', () => {
    describe('route definitions', () => {
        it('should generate correct collection routes', () => {
            const testDatasetId = 'root-123';
            const testCollectionType = 'image';
            const testCollectionId = '123';
            expect(
                routes.collection.images(testDatasetId, testCollectionType, testCollectionId)
            ).toBe('/datasets/root-123/image/123/images');
            expect(
                routes.collection.annotations(testDatasetId, testCollectionType, testCollectionId)
            ).toBe('/datasets/root-123/image/123/annotations');
        });
    });

    describe('route classification', () => {
        it('detects the evaluation compare route', () => {
            expect(isEvaluationCompareRoute(APP_ROUTES.evaluationCompare)).toBe(true);
            expect(isEvaluationCompareRoute(APP_ROUTES.images)).toBe(false);
        });

        describe('collection-grid routes', () => {
            it('images route is classified as a grid route', () => {
                expect(isImagesRoute(APP_ROUTES.images)).toBe(true);
            });

            it('annotations route is classified as a grid route', () => {
                expect(isAnnotationsRoute(APP_ROUTES.annotations)).toBe(true);
            });

            it('videos route is classified as a grid route', () => {
                expect(isVideosRoute(APP_ROUTES.videos)).toBe(true);
            });

            it('frames route is classified as a grid route', () => {
                expect(isVideoFramesRoute(APP_ROUTES.frames)).toBe(true);
            });

            it('groups route is classified as a grid route', () => {
                expect(isGroupsRoute(APP_ROUTES.groups)).toBe(true);
            });
        });

        describe('details routes', () => {
            it('image details route is classified as a sample-details route', () => {
                expect(isSampleDetailsRoute(APP_ROUTES.imageDetails)).toBe(true);
            });

            it('image details route is not classified as a grid route', () => {
                expect(isImagesRoute(APP_ROUTES.imageDetails)).toBe(false);
            });

            it('annotation details route is classified as an annotation-details route', () => {
                expect(isAnnotationDetailsRoute(APP_ROUTES.annotationDetails)).toBe(true);
            });

            it('video details route is classified as a video-details route', () => {
                expect(isVideoDetailsRoute(APP_ROUTES.videoDetails)).toBe(true);
            });

            it('frame details route is classified as a frame-details route', () => {
                expect(isFrameDetailsRoute(APP_ROUTES.framesDetails)).toBe(true);
            });

            it('point-cloud labeling route is classified as a point-cloud-labeling route', () => {
                expect(isPointCloudLabelingRoute(APP_ROUTES.pointCloudLabeling)).toBe(true);
            });

            it('point-cloud labeling route is not classified as an MCAP sequences grid route', () => {
                expect(isMcapSequencesRoute(APP_ROUTES.pointCloudLabeling)).toBe(false);
            });
        });
    });

    describe('routeHelpers', () => {
        const testDatasetId = 'root-123';
        const testCollectionType = 'image';
        const testCollectionId = '123';

        it('should generate the evaluation compare route with the run IDs', () => {
            expect(
                routeHelpers.toEvaluationCompare(
                    testDatasetId,
                    testCollectionType,
                    testCollectionId,
                    ['run-1', 'run-2']
                )
            ).toBe('/datasets/root-123/image/123/evaluation/compare?runs=run-1,run-2');
        });

        it('should generate correct images route', () => {
            expect(routeHelpers.toImages(testDatasetId, testCollectionType, testCollectionId)).toBe(
                '/datasets/root-123/image/123/images'
            );
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
                `/datasets/${testDatasetId}/${testCollectionType}/${testCollectionId}/images/${testSampleId}`
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

        it('should generate correct mcap-sequences route', () => {
            expect(
                routeHelpers.toMcapSequences(testDatasetId, testCollectionType, testCollectionId)
            ).toBe(
                `/datasets/${testDatasetId}/${testCollectionType}/${testCollectionId}/mcap-sequences`
            );
        });

        it('should generate correct point-cloud labeling route', () => {
            const testSequenceId = 'seq-789';
            expect(
                routeHelpers.toPointCloudLabeling({
                    datasetId: testDatasetId,
                    collectionType: testCollectionType,
                    collectionId: testCollectionId,
                    sequenceId: testSequenceId
                })
            ).toBe(
                `/datasets/${testDatasetId}/${testCollectionType}/${testCollectionId}/mcap-sequences/${testSequenceId}`
            );
        });

        it('should generate correct point-cloud labeling route with group id', () => {
            const testSequenceId = 'seq-789';
            expect(
                routeHelpers.toPointCloudLabeling({
                    datasetId: testDatasetId,
                    collectionType: testCollectionType,
                    collectionId: testCollectionId,
                    sequenceId: testSequenceId,
                    groupId: 'group-1'
                })
            ).toBe(
                `/datasets/${testDatasetId}/${testCollectionType}/${testCollectionId}/mcap-sequences/${testSequenceId}?group_id=group-1`
            );
        });
    });
});
