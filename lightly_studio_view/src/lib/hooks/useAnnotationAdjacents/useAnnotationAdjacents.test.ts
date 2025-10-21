import { get } from 'svelte/store';
import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest';
import { useAnnotationAdjacents, UseAnnotationAdjacentsResult } from './useAnnotationAdjacents';
import * as sdkModule from '$lib/api/lightly_studio_local/sdk.gen';
import type {
    AnnotationViewsWithCount,
    AnnotationWithSampleView
} from '../../api/lightly_studio_local';

describe('useAnnotationAdjacents', () => {
    let errorSpy: ReturnType<typeof vi.spyOn>;

    const flushPromises = () => new Promise((resolve) => setImmediate(resolve));

    const getResult = (result: unknown) =>
        get<UseAnnotationAdjacentsResult>(result as unknown as UseAnnotationAdjacentsResult);

    beforeAll(() => {
        errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    });

    afterAll(() => {
        errorSpy.mockRestore();
    });

    const mockAnnotation = {
        annotation_id: 'test-annotation',
        dataset_id: 'test-dataset',
        annotation_label: {
            annotation_label_name: 'test-annotation-label'
        },
        sample_id: 'test-sample',
        sample: {
            file_path_abs: '/path/to/sample.jpg',
            file_name: 'sample.jpg',
            dataset_id: 'test-dataset',
            sample_id: 'test-sample',
            width: 1000,
            height: 1000
        },
        annotation_label_id: 'test-label',
        annotation_type: 'object_detection' as const,
        object_detection_details: {
            bbox: [0, 0, 100, 100],
            confidence: 0.95,
            x: 0,
            y: 0,
            width: 100,
            height: 100
        },
        instance_segmentation_details: undefined,
        semantic_segmentation_details: undefined
    } as AnnotationWithSampleView;

    const mockAnnotations: AnnotationViewsWithCount = {
        data: [
            { ...mockAnnotation, annotation_id: 'prev-annotation' },
            { ...mockAnnotation, annotation_id: 'current-annotation' },
            { ...mockAnnotation, annotation_id: 'next-annotation' }
        ],
        total_count: 3,
        nextCursor: 3
    };

    it('should initialize with loading state and fetch adjacent annotations', async () => {
        vi.spyOn(sdkModule, 'readAnnotations').mockResolvedValueOnce({
            data: mockAnnotations,
            request: undefined,
            response: undefined
        });

        const result = useAnnotationAdjacents({
            dataset_id: 'test-dataset',
            currentAnnotationId: 'current-annotation',
            annotationIndex: 1
        });

        // Initially loading
        expect(getResult(result).isLoading).toBe(true);
        expect(getResult(result).data).toBeUndefined();
        expect(getResult(result).error).toBeUndefined();

        await flushPromises();

        // After fetch
        expect(getResult(result).isLoading).toBe(false);
        expect(getResult(result).data).toEqual({
            annotationPrevious: mockAnnotations.data[0],
            annotationNext: mockAnnotations.data[2]
        });
        expect(getResult(result).error).toBeUndefined();
    });

    it('returns only annotationNext at the start of the list', async () => {
        const firstAnnotationData = [
            { ...mockAnnotation, annotation_id: 'current-annotation' },
            { ...mockAnnotation, annotation_id: 'next-annotation' },
            { ...mockAnnotation, annotation_id: 'next-annotation2' }
        ];

        vi.spyOn(sdkModule, 'readAnnotations').mockResolvedValueOnce({
            data: {
                data: firstAnnotationData,
                total_count: 3,
                nextCursor: 3
            },
            request: undefined,
            response: undefined
        });

        const result = useAnnotationAdjacents({
            dataset_id: 'test-dataset',
            currentAnnotationId: 'current-annotation',
            annotationIndex: 0
        });

        await flushPromises();

        expect(get<UseAnnotationAdjacentsResult>(result).data).toEqual({
            annotationPrevious: undefined,
            annotationNext: firstAnnotationData[1]
        });
        expect(get<UseAnnotationAdjacentsResult>(result).isLoading).toBe(false);
        expect(get<UseAnnotationAdjacentsResult>(result).error).toBeUndefined();
    });

    it('returns annotationNext and annotationPrevious in the middle of the list', async () => {
        const middleAnnotationData = [
            { ...mockAnnotation, annotation_id: 'prev-annotation' },
            { ...mockAnnotation, annotation_id: 'current-annotation' },
            { ...mockAnnotation, annotation_id: 'next-annotation' }
        ];

        vi.spyOn(sdkModule, 'readAnnotations').mockResolvedValueOnce({
            data: {
                data: middleAnnotationData,
                total_count: 3,
                nextCursor: 3
            },
            request: undefined,
            response: undefined
        });

        const result = useAnnotationAdjacents({
            dataset_id: 'test-dataset',
            currentAnnotationId: 'current-annotation',
            annotationIndex: 1
        });

        await flushPromises();

        expect(get<UseAnnotationAdjacentsResult>(result).data).toEqual({
            annotationPrevious: middleAnnotationData[0],
            annotationNext: middleAnnotationData[2]
        });
        expect(get<UseAnnotationAdjacentsResult>(result).isLoading).toBe(false);
        expect(get<UseAnnotationAdjacentsResult>(result).error).toBeUndefined();
    });

    it('returns only annotationPrevious at the end of the list', async () => {
        const endAnnotationData = [
            { ...mockAnnotation, annotation_id: 'prev-annotation' },
            { ...mockAnnotation, annotation_id: 'current-annotation' }
        ];

        vi.spyOn(sdkModule, 'readAnnotations').mockResolvedValueOnce({
            data: {
                data: endAnnotationData,
                total_count: 2,
                nextCursor: 2
            },
            request: undefined,
            response: undefined
        });

        const result = useAnnotationAdjacents({
            dataset_id: 'test-dataset',
            currentAnnotationId: 'current-annotation',
            annotationIndex: 1
        });

        await flushPromises();

        expect(getResult(result).data).toEqual({
            annotationPrevious: endAnnotationData[0],
            annotationNext: undefined
        });
        expect(getResult(result).isLoading).toBe(false);
        expect(getResult(result).error).toBeUndefined();
    });

    it('returns annotationPrevious and annotationNext as undefined for 1 annotation', async () => {
        const singleAnnotationData = [{ ...mockAnnotation, annotation_id: 'current-annotation' }];

        vi.spyOn(sdkModule, 'readAnnotations').mockResolvedValueOnce({
            data: {
                data: singleAnnotationData,
                total_count: 1,
                nextCursor: 1
            },
            request: undefined,
            response: undefined
        });

        const result = useAnnotationAdjacents({
            dataset_id: 'test-dataset',
            currentAnnotationId: 'current-annotation',
            annotationIndex: 0
        });

        await flushPromises();

        expect(getResult(result).data).toEqual({
            annotationPrevious: undefined,
            annotationNext: undefined
        });
        expect(getResult(result).isLoading).toBe(false);
        expect(getResult(result).error).toBeUndefined();
    });

    it('should handle API errors correctly', async () => {
        const errorMessage = 'Failed to load annotations';
        vi.spyOn(sdkModule, 'readAnnotations').mockRejectedValueOnce(new Error(errorMessage));

        const result = useAnnotationAdjacents({
            dataset_id: 'test-dataset',
            annotationIndex: 1,
            currentAnnotationId: 'current-annotation'
        });

        await flushPromises();

        expect(getResult(result).isLoading).toBe(false);
        expect(getResult(result).data).toBeUndefined();
        expect(getResult(result).error).toBe(`Error: ${errorMessage}`);
    });

    it('treats empty result as no annotations', async () => {
        vi.spyOn(sdkModule, 'readAnnotations').mockResolvedValueOnce({
            data: { data: [], total_count: 0, nextCursor: 0 },
            request: undefined,
            response: undefined
        });

        const result = useAnnotationAdjacents({
            dataset_id: 'test-dataset',
            annotationIndex: 0,
            currentAnnotationId: 'current-annotation'
        });

        await flushPromises();

        expect(getResult(result).data).toEqual({
            annotationPrevious: undefined,
            annotationNext: undefined
        });
        expect(getResult(result).isLoading).toBe(false);
        expect(getResult(result).error).toBeUndefined();
    });

    it('should handle API returning undefined data', async () => {
        vi.spyOn(sdkModule, 'readAnnotations').mockResolvedValueOnce({
            data: undefined,
            response: undefined,
            request: undefined
        });

        const result = useAnnotationAdjacents({
            dataset_id: 'test-dataset',
            annotationIndex: 1,
            currentAnnotationId: 'current-annotation'
        });

        await flushPromises();

        expect(getResult(result).isLoading).toBe(false);
        expect(getResult(result).data).toBeUndefined();
        expect(getResult(result).error).toBe('No annotations data received');
    });

    it('should pass through all loading parameters correctly', async () => {
        const loadAnnotationsSpy = vi.spyOn(sdkModule, 'readAnnotations').mockResolvedValueOnce({
            data: mockAnnotations,
            request: undefined,
            response: undefined
        });

        const params = {
            dataset_id: 'test-dataset',
            annotationIndex: 1,
            annotation_label_ids: ['label1', 'label2'],
            tag_ids: ['tag1', 'tag2'],
            currentAnnotationId: 'current-annotation'
        };

        useAnnotationAdjacents(params);

        expect(loadAnnotationsSpy).toHaveBeenCalledWith({
            path: { dataset_id: 'test-dataset' },
            query: {
                cursor: 0, // we pass offset as annotationIndex - 1, to load previous annotation
                limit: 3,
                annotation_label_ids: ['label1', 'label2'],
                tag_ids: ['tag1', 'tag2']
            }
        });
    });
});
