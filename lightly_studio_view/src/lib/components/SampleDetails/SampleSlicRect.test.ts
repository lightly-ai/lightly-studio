import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SampleSlicRect from './SampleSlicRect/SampleSlicRect.svelte';

const {
    mockAnnotationContext,
    mockToolbarContext,
    finishBrushMock,
    loadSuperpixelsForImageMock,
    setAnnotationIdMock,
    setIsDrawingMock,
    updateAnnotationMock,
    getImageCoordsFromMouseMock,
    getLabelAtPointMock,
    maskToColoredDataUrlMock,
    queuedPoints,
    invalidateQueriesMock,
    setQueryDataMock
} = vi.hoisted(() => {
    const annotationContext = {
        annotationId: null as string | null,
        isDrawing: false,
        isOnAnnotationDetailsView: false,
        lockedAnnotationIds: new Set<string>()
    };
    const toolbarContext = {
        status: 'slic' as const,
        slic: {
            level: 'medium' as 'coarse' | 'medium' | 'fine',
            status: 'idle' as 'idle' | 'computing' | 'ready' | 'error'
        }
    };

    return {
        mockAnnotationContext: annotationContext,
        mockToolbarContext: toolbarContext,
        finishBrushMock: vi.fn(),
        loadSuperpixelsForImageMock: vi.fn(async () => ({
            labels: new Int32Array([0, 1, 2]),
            width: 3,
            height: 1,
            boundaries: new Uint8Array([1, 1, 1]),
            labelPixelIndexes: [[0], [1], [2]],
            originalWidth: 3,
            originalHeight: 1,
            scaleX: 1,
            scaleY: 1,
            level: 'medium'
        })),
        setAnnotationIdMock: vi.fn((id: string | null) => {
            annotationContext.annotationId = id;
        }),
        setIsDrawingMock: vi.fn((value: boolean) => {
            annotationContext.isDrawing = value;
        }),
        updateAnnotationMock: vi.fn(),
        maskToColoredDataUrlMock: vi.fn(() => 'data:image/png;base64,mock'),
        queuedPoints: [] as { x: number; y: number }[],
        invalidateQueriesMock: vi.fn(() => Promise.resolve()),
        setQueryDataMock: vi.fn(),
        getImageCoordsFromMouseMock: vi.fn(() => queuedPoints.shift() ?? { x: 0, y: 0 }),
        getLabelAtPointMock: vi.fn((_, x: number) => Math.max(0, Math.min(2, Math.round(x))))
    };
});

vi.mock('$app/state', () => ({
    page: {
        params: {
            dataset_id: 'dataset-1'
        }
    }
}));

vi.mock('@tanstack/svelte-query', () => ({
    useQueryClient: () => ({
        invalidateQueries: invalidateQueriesMock,
        setQueryData: setQueryDataMock
    })
}));

vi.mock('$lib/api/lightly_studio_local/@tanstack/svelte-query.gen', () => ({
    getAnnotationOptions: ({ path }: { path: { annotation_id: string; collection_id: string } }) => ({
        queryKey: ['annotation', path.collection_id, path.annotation_id]
    }),
    readAnnotationLabelsOptions: ({ path }: { path: { collection_id: string } }) => ({
        queryKey: ['annotation-labels', path.collection_id]
    }),
    readImageOptions: ({ path }: { path: { sample_id: string } }) => ({
        queryKey: ['image', path.sample_id]
    })
}));

vi.mock('$lib/hooks/useAnnotationCounts/useAnnotationCounts', () => ({
    useAnnotationCountsQueryKey: ['annotation-counts']
}));

vi.mock('$lib/components/SampleAnnotation/utils', () => ({
    decodeRLEToBinaryMask: vi.fn(() => new Uint8Array([0, 0, 0])),
    getImageCoordsFromMouse: getImageCoordsFromMouseMock,
    interpolateLineBetweenPoints: vi.fn((from: { x: number; y: number }, to: { x: number; y: number }) => {
        const points = [{ x: from.x, y: from.y }];

        if (Math.abs(to.x - from.x) > 1) {
            points.push({ x: 1, y: from.y });
        }

        points.push({ x: to.x, y: to.y });
        return points;
    })
}));

vi.mock(
    '$lib/components/SampleAnnotation/SampleAnnotationSegmentationRLE/calculateBinaryMaskFromRLE/parseColor',
    () => ({
        default: vi.fn(() => ({ r: 0, g: 0, b: 255, a: 255 }))
    })
);

vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({
        context: mockAnnotationContext,
        setAnnotationId: setAnnotationIdMock,
        setIsDrawing: setIsDrawingMock
    })
}));

vi.mock('$lib/contexts/SampleDetailsToolbar.svelte', () => ({
    useSampleDetailsToolbarContext: () => ({
        context: mockToolbarContext,
        setSlicStatus(status: 'idle' | 'computing' | 'ready' | 'error') {
            mockToolbarContext.slic.status = status;
        }
    })
}));

vi.mock('$lib/hooks/useAnnotation/useAnnotation', () => ({
    useAnnotation: () => ({
        updateAnnotation: updateAnnotationMock
    })
}));

vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: () =>
        writable({
            data: []
        })
}));

vi.mock('$lib/hooks/useCollection/useCollection', () => ({
    useCollectionWithChildren: () => ({
        refetch: vi.fn()
    })
}));

vi.mock('$lib/hooks/useInstanceSegmentationBrush', () => ({
    useInstanceSegmentationBrush: () => ({
        finishBrush: finishBrushMock
    })
}));

vi.mock('$lib/utils/slic', () => ({
    loadSuperpixelsForImage: loadSuperpixelsForImageMock,
    createSlicMaskForLabels: vi.fn((result, labelIds: Iterable<number>) => {
        const mask = new Uint8Array(result.width * result.height);
        for (const labelId of labelIds) {
            for (const pixelIndex of result.labelPixelIndexes[labelId] ?? []) {
                mask[pixelIndex] = 1;
            }
        }
        return mask;
    }),
    getLabelAtPoint: getLabelAtPointMock,
    extractCellMask: vi.fn(() => new Uint8Array([0, 1, 0])),
    upsampleCellMask: vi.fn((result, labelId) => {
        const mask = new Uint8Array(result.originalWidth * result.originalHeight);
        for (const pixelIndex of result.labelPixelIndexes[labelId] ?? []) {
            mask[pixelIndex] = 1;
        }
        return mask;
    }),
    maskToColoredDataUrl: maskToColoredDataUrlMock
}));

describe('SampleSlicRect', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockAnnotationContext.annotationId = null;
        mockAnnotationContext.isDrawing = false;
        mockAnnotationContext.lockedAnnotationIds = new Set<string>();
        mockToolbarContext.slic.level = 'medium';
        mockToolbarContext.slic.status = 'idle';
        queuedPoints.length = 0;
        loadSuperpixelsForImageMock.mockClear();
        finishBrushMock.mockImplementation(() => null);
        maskToColoredDataUrlMock.mockClear();
        invalidateQueriesMock.mockClear();
        setQueryDataMock.mockClear();
        getImageCoordsFromMouseMock.mockImplementation(() => queuedPoints.shift() ?? { x: 0, y: 0 });
        getLabelAtPointMock.mockImplementation((_, x: number) =>
            Math.max(0, Math.min(2, Math.round(x)))
        );
    });

    it('loads superpixels when the slic tool is active', async () => {
        render(SampleSlicRect, {
            props: {
                sample: { width: 3, height: 1, annotations: [] },
                sampleId: 'sample-1',
                collectionId: 'collection-1',
                drawerStrokeColor: 'rgb(0, 0, 255)',
                imageUrl: 'https://example.com/image.png',
                refetch: vi.fn()
            }
        });

        await waitFor(() => {
            expect(mockToolbarContext.slic.status).toBe('ready');
        });
    });

    it('commits a stroke through the brush persistence flow on pointerup', async () => {
        const { container } = render(SampleSlicRect, {
            props: {
                sample: { width: 3, height: 1, annotations: [] },
                sampleId: 'sample-2',
                collectionId: 'collection-1',
                drawerStrokeColor: 'rgb(0, 0, 255)',
                imageUrl: 'https://example.com/image.png',
                refetch: vi.fn()
            }
        });

        await waitFor(() => {
            expect(mockToolbarContext.slic.status).toBe('ready');
        });

        const rect = container.querySelector('rect');
        expect(rect).not.toBeNull();

        queuedPoints.push({ x: 0, y: 0 }, { x: 1, y: 0 });
        await fireEvent.pointerDown(rect as SVGRectElement, {
            pointerId: 1,
            clientX: 0,
            clientY: 0
        });
        await fireEvent.pointerMove(rect as SVGRectElement, {
            pointerId: 1,
            clientX: 1,
            clientY: 0
        });
        await fireEvent.pointerUp(rect as SVGRectElement, {
            pointerId: 1,
            clientX: 1,
            clientY: 0
        });

        expect(setIsDrawingMock).toHaveBeenCalledWith(true);
        expect(finishBrushMock).toHaveBeenCalledTimes(1);
    });

    it('commits a single clicked label through direct original-image painting', async () => {
        const { container } = render(SampleSlicRect, {
            props: {
                sample: { width: 3, height: 1, annotations: [] },
                sampleId: 'sample-single',
                collectionId: 'collection-1',
                drawerStrokeColor: 'rgb(0, 0, 255)',
                imageUrl: 'https://example.com/image.png',
                refetch: vi.fn()
            }
        });

        await waitFor(() => {
            expect(mockToolbarContext.slic.status).toBe('ready');
        });

        const rect = container.querySelector('rect');
        expect(rect).not.toBeNull();

        queuedPoints.push({ x: 1, y: 0 });
        await fireEvent.pointerDown(rect as SVGRectElement, {
            pointerId: 1,
            clientX: 1,
            clientY: 0
        });
        await fireEvent.pointerUp(rect as SVGRectElement, {
            pointerId: 1,
            clientX: 1,
            clientY: 0
        });

        const persistedMask = finishBrushMock.mock.calls[0][0] as Uint8Array;
        expect(Array.from(persistedMask)).toEqual([0, 1, 0]);
    });

    it('updates the drag preview without rebuilding the full-resolution mask on pointermove', async () => {
        const { container } = render(SampleSlicRect, {
            props: {
                sample: { width: 3, height: 1, annotations: [] },
                sampleId: 'sample-preview',
                collectionId: 'collection-1',
                drawerStrokeColor: 'rgb(0, 0, 255)',
                imageUrl: 'https://example.com/image.png',
                refetch: vi.fn()
            }
        });

        await waitFor(() => {
            expect(mockToolbarContext.slic.status).toBe('ready');
        });

        const rect = container.querySelector('rect');
        expect(rect).not.toBeNull();

        queuedPoints.push({ x: 0, y: 0 }, { x: 2, y: 0 });
        await fireEvent.pointerDown(rect as SVGRectElement, {
            pointerId: 1,
            clientX: 0,
            clientY: 0
        });

        await fireEvent.pointerMove(rect as SVGRectElement, {
            pointerId: 1,
            clientX: 2,
            clientY: 0
        });

        expect(maskToColoredDataUrlMock).toHaveBeenCalled();

        await fireEvent.pointerUp(rect as SVGRectElement, {
            pointerId: 1,
            clientX: 2,
            clientY: 0
        });
    });

    it('captures middle cells during a fast stroke via interpolation', async () => {
        const { container } = render(SampleSlicRect, {
            props: {
                sample: { width: 3, height: 1, annotations: [] },
                sampleId: 'sample-middle',
                collectionId: 'collection-1',
                drawerStrokeColor: 'rgb(0, 0, 255)',
                imageUrl: 'https://example.com/image.png',
                refetch: vi.fn()
            }
        });

        await waitFor(() => {
            expect(mockToolbarContext.slic.status).toBe('ready');
        });

        const rect = container.querySelector('rect');
        expect(rect).not.toBeNull();

        queuedPoints.push({ x: 0, y: 0 }, { x: 2, y: 0 });
        await fireEvent.pointerDown(rect as SVGRectElement, {
            pointerId: 1,
            clientX: 0,
            clientY: 0
        });
        await fireEvent.pointerMove(rect as SVGRectElement, {
            pointerId: 1,
            clientX: 2,
            clientY: 0
        });
        await fireEvent.pointerUp(rect as SVGRectElement, {
            pointerId: 1,
            clientX: 2,
            clientY: 0
        });

        const persistedMask = finishBrushMock.mock.calls[0][0] as Uint8Array;
        expect(Array.from(persistedMask)).toEqual([1, 1, 1]);
    });

    it('toggles each cell only once per stroke even when re-entered', async () => {
        const { container } = render(SampleSlicRect, {
            props: {
                sample: { width: 3, height: 1, annotations: [] },
                sampleId: 'sample-repeat',
                collectionId: 'collection-1',
                drawerStrokeColor: 'rgb(0, 0, 255)',
                imageUrl: 'https://example.com/image.png',
                refetch: vi.fn()
            }
        });

        await waitFor(() => {
            expect(mockToolbarContext.slic.status).toBe('ready');
        });

        const rect = container.querySelector('rect');
        expect(rect).not.toBeNull();

        queuedPoints.push({ x: 1, y: 0 }, { x: 2, y: 0 }, { x: 1, y: 0 });
        await fireEvent.pointerDown(rect as SVGRectElement, {
            pointerId: 1,
            clientX: 1,
            clientY: 0
        });
        await fireEvent.pointerMove(rect as SVGRectElement, {
            pointerId: 1,
            clientX: 2,
            clientY: 0
        });
        await fireEvent.pointerMove(rect as SVGRectElement, {
            pointerId: 1,
            clientX: 1,
            clientY: 0
        });
        await fireEvent.pointerUp(rect as SVGRectElement, {
            pointerId: 1,
            clientX: 1,
            clientY: 0
        });

        const persistedMask = finishBrushMock.mock.calls[0][0] as Uint8Array;
        expect(Array.from(persistedMask)).toEqual([0, 1, 1]);
    });

    it('blocks a new stroke while a save is in flight', async () => {
        let resolveFinish: (() => void) | undefined;
        finishBrushMock.mockImplementation(
            () =>
                new Promise((resolve) => {
                    resolveFinish = () => resolve(null);
                })
        );

        const { container } = render(SampleSlicRect, {
            props: {
                sample: { width: 3, height: 1, annotations: [] },
                sampleId: 'sample-3',
                collectionId: 'collection-1',
                drawerStrokeColor: 'rgb(0, 0, 255)',
                imageUrl: 'https://example.com/image.png',
                refetch: vi.fn()
            }
        });

        await waitFor(() => {
            expect(mockToolbarContext.slic.status).toBe('ready');
        });

        const rect = container.querySelector('rect');
        expect(rect).not.toBeNull();

        queuedPoints.push({ x: 0, y: 0 }, { x: 1, y: 0 });
        await fireEvent.pointerDown(rect as SVGRectElement, {
            pointerId: 1,
            clientX: 0,
            clientY: 0
        });
        await fireEvent.pointerUp(rect as SVGRectElement, {
            pointerId: 1,
            clientX: 0,
            clientY: 0
        });

        queuedPoints.push({ x: 1, y: 0 });
        await fireEvent.pointerDown(rect as SVGRectElement, {
            pointerId: 2,
            clientX: 1,
            clientY: 0
        });
        await fireEvent.pointerUp(rect as SVGRectElement, {
            pointerId: 2,
            clientX: 1,
            clientY: 0
        });

        expect(finishBrushMock).toHaveBeenCalledTimes(1);

        resolveFinish?.();
    });

    it('does not reload superpixels again when saving a stroke', async () => {
        const { container } = render(SampleSlicRect, {
            props: {
                sample: { width: 3, height: 1, annotations: [] },
                sampleId: 'sample-no-reload',
                collectionId: 'collection-1',
                drawerStrokeColor: 'rgb(0, 0, 255)',
                imageUrl: 'https://example.com/image.png',
                refetch: vi.fn()
            }
        });

        await waitFor(() => {
            expect(mockToolbarContext.slic.status).toBe('ready');
        });

        const rect = container.querySelector('rect');
        expect(rect).not.toBeNull();

        queuedPoints.push({ x: 0, y: 0 });
        await fireEvent.pointerDown(rect as SVGRectElement, {
            pointerId: 1,
            clientX: 0,
            clientY: 0
        });
        await fireEvent.pointerUp(rect as SVGRectElement, {
            pointerId: 1,
            clientX: 0,
            clientY: 0
        });

        expect(loadSuperpixelsForImageMock).toHaveBeenCalledTimes(1);
    });

    it('defers image invalidation and avoids patching full segmentation payloads into the sample cache', async () => {
        vi.useFakeTimers();
        finishBrushMock.mockImplementation(async (...args) => {
            const options = args[5] as {
                refreshAnnotations?: (annotation: {
                    sample_id: string;
                    parent_sample_id: string;
                    annotation_type: string;
                    annotation_label: { annotation_label_name: string };
                    created_at: Date;
                    segmentation_details: {
                        x: number;
                        y: number;
                        width: number;
                        height: number;
                        segmentation_mask: number[];
                    };
                }) => Promise<void>;
            };

            const persistedAnnotation = {
                sample_id: 'created-annotation',
                parent_sample_id: 'sample-cache',
                annotation_type: 'instance_segmentation',
                annotation_label: {
                    annotation_label_name: 'DEFAULT'
                },
                created_at: new Date(),
                segmentation_details: {
                    x: 0,
                    y: 0,
                    width: 1,
                    height: 1,
                    segmentation_mask: [0, 1, 0]
                }
            };

            await options.refreshAnnotations?.(persistedAnnotation);

            return persistedAnnotation;
        });

        const { container, rerender } = render(SampleSlicRect, {
            props: {
                sample: { width: 3, height: 1, annotations: [] },
                sampleId: 'sample-cache',
                collectionId: 'collection-1',
                drawerStrokeColor: 'rgb(0, 0, 255)',
                imageUrl: 'https://example.com/image.png',
                refetch: vi.fn()
            }
        });

        await waitFor(() => {
            expect(mockToolbarContext.slic.status).toBe('ready');
        });

        const rect = container.querySelector('rect');
        expect(rect).not.toBeNull();

        queuedPoints.push({ x: 0, y: 0 });
        await fireEvent.pointerDown(rect as SVGRectElement, {
            pointerId: 1,
            clientX: 0,
            clientY: 0
        });
        await fireEvent.pointerUp(rect as SVGRectElement, {
            pointerId: 1,
            clientX: 0,
            clientY: 0
        });

        expect(mockAnnotationContext.isDrawing).toBe(true);
        expect(setQueryDataMock).toHaveBeenCalled();
        const imagePatchCall = setQueryDataMock.mock.calls.find((call) => call[0][0] === 'image');
        expect(imagePatchCall).toBeDefined();
        const patchedImage = imagePatchCall?.[1]({
            annotations: []
        });
        expect(patchedImage.annotations[0].segmentation_details).toBeNull();

        expect(invalidateQueriesMock).toHaveBeenCalledWith({
            queryKey: ['annotation-labels', 'collection-1']
        });
        expect(invalidateQueriesMock).toHaveBeenCalledWith({
            queryKey: ['annotation-counts']
        });

        expect(invalidateQueriesMock).not.toHaveBeenCalledWith({
            queryKey: ['image', 'sample-cache']
        });

        vi.runAllTimers();

        expect(invalidateQueriesMock).toHaveBeenCalledWith({
            queryKey: ['image', 'sample-cache']
        });
        expect(invalidateQueriesMock).toHaveBeenCalledWith({
            queryKey: ['annotation', 'collection-1', 'created-annotation']
        });

        await rerender({
            sample: {
                width: 3,
                height: 1,
                annotations: [
                    {
                        sample_id: 'created-annotation',
                        parent_sample_id: 'sample-cache',
                        annotation_type: 'instance_segmentation',
                        annotation_label: {
                            annotation_label_name: 'DEFAULT'
                        },
                        created_at: new Date(),
                        segmentation_details: {
                            x: 0,
                            y: 0,
                            width: 1,
                            height: 1,
                            segmentation_mask: [0, 1, 0]
                        }
                    }
                ]
            },
            sampleId: 'sample-cache',
            collectionId: 'collection-1',
            drawerStrokeColor: 'rgb(0, 0, 255)',
            imageUrl: 'https://example.com/image.png',
            refetch: vi.fn()
        });

        await waitFor(() => {
            expect(mockAnnotationContext.isDrawing).toBe(false);
        });

        vi.useRealTimers();
    });
});
