import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import SampleSlicRect from './SampleSlicRect.svelte';

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
    queuedPoints
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

vi.mock('$lib/components/SampleAnnotation/utils', () => ({
    decodeRLEToBinaryMask: vi.fn(() => new Uint8Array([0, 0, 0])),
    getImageCoordsFromMouse: getImageCoordsFromMouseMock,
    interpolateLineBetweenPoints: vi.fn(
        (from: { x: number; y: number }, to: { x: number; y: number }) => {
            const points = [{ x: from.x, y: from.y }];

            if (Math.abs(to.x - from.x) > 1) {
                points.push({ x: 1, y: from.y });
            }

            points.push({ x: to.x, y: to.y });
            return points;
        }
    )
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
    useAnnotationLabels: () => ({
        data: []
    })
}));

vi.mock('$lib/hooks/useDeleteAnnotation/useDeleteAnnotation', () => ({
    useDeleteAnnotation: () => ({
        deleteAnnotation: vi.fn()
    })
}));

vi.mock('$lib/hooks/useSelectClassDialog/useSelectClassDialog', () => ({
    useSelectClassDialog: () => ({
        open: writable(false),
        requestLabel: vi.fn(async () => null),
        handleConfirm: vi.fn(),
        handleCancel: vi.fn()
    })
}));

vi.mock('$lib/hooks/useCollection/useCollection', () => ({
    useCollectionWithChildren: () => ({
        refetch: vi.fn()
    })
}));

vi.mock('$lib/hooks/useSegmentationMaskBrush', () => ({
    useSegmentationMaskBrush: () => ({
        finishBrush: finishBrushMock
    })
}));

// The pure mask/stroke logic (accumulateStrokeLabels, applySegmentToMask, …)
// is imported straight from @lightly-ai/slic and runs for real; only the
// app-side adapter is mocked (canvas rasterization and the async load).
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
    maskToColoredDataUrl: maskToColoredDataUrlMock
}));

/** Render with default props and wait until superpixels are loaded. */
const renderReady = async (sampleId: string) => {
    const { container } = render(SampleSlicRect, {
        props: {
            sample: { width: 3, height: 1, annotations: [] },
            sampleId,
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
    return rect as SVGRectElement;
};

/** Fire a pointer stroke through the given points (down, moves, up). */
const stroke = async (rect: SVGRectElement, points: { x: number; y: number }[], pointerId = 1) => {
    queuedPoints.push(...points);

    const [first, ...rest] = points;
    await fireEvent.pointerDown(rect, { pointerId, clientX: first.x, clientY: first.y });
    for (const point of rest) {
        await fireEvent.pointerMove(rect, { pointerId, clientX: point.x, clientY: point.y });
    }
    const last = points[points.length - 1];
    await fireEvent.pointerUp(rect, { pointerId, clientX: last.x, clientY: last.y });
};

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
        getImageCoordsFromMouseMock.mockImplementation(
            () => queuedPoints.shift() ?? { x: 0, y: 0 }
        );
        getLabelAtPointMock.mockImplementation((_, x: number) =>
            Math.max(0, Math.min(2, Math.round(x)))
        );
    });

    it('loads superpixels when the slic tool is active', async () => {
        await renderReady('sample-1');
    });

    it('commits a stroke through the brush persistence flow on pointerup', async () => {
        const rect = await renderReady('sample-2');

        await stroke(rect, [
            { x: 0, y: 0 },
            { x: 1, y: 0 }
        ]);

        expect(setIsDrawingMock).toHaveBeenCalledWith(true);
        expect(finishBrushMock).toHaveBeenCalledTimes(1);
    });

    it('commits a single clicked label through direct original-image painting', async () => {
        const rect = await renderReady('sample-single');

        await stroke(rect, [{ x: 1, y: 0 }]);

        const persistedMask = finishBrushMock.mock.calls[0][0] as Uint8Array;
        expect(Array.from(persistedMask)).toEqual([0, 1, 0]);
    });

    it('updates the drag preview without rebuilding the full-resolution mask on pointermove', async () => {
        const rect = await renderReady('sample-preview');

        queuedPoints.push({ x: 0, y: 0 }, { x: 2, y: 0 });
        await fireEvent.pointerDown(rect, { pointerId: 1, clientX: 0, clientY: 0 });
        await fireEvent.pointerMove(rect, { pointerId: 1, clientX: 2, clientY: 0 });

        expect(maskToColoredDataUrlMock).toHaveBeenCalled();

        await fireEvent.pointerUp(rect, { pointerId: 1, clientX: 2, clientY: 0 });
    });

    it('captures middle cells during a fast stroke via interpolation', async () => {
        const rect = await renderReady('sample-middle');

        await stroke(rect, [
            { x: 0, y: 0 },
            { x: 2, y: 0 }
        ]);

        const persistedMask = finishBrushMock.mock.calls[0][0] as Uint8Array;
        expect(Array.from(persistedMask)).toEqual([1, 1, 1]);
    });

    it('toggles each cell only once per stroke even when re-entered', async () => {
        const rect = await renderReady('sample-repeat');

        await stroke(rect, [
            { x: 1, y: 0 },
            { x: 2, y: 0 },
            { x: 1, y: 0 }
        ]);

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

        const rect = await renderReady('sample-3');

        await stroke(rect, [{ x: 0, y: 0 }]);
        await stroke(rect, [{ x: 1, y: 0 }], 2);

        expect(finishBrushMock).toHaveBeenCalledTimes(1);

        resolveFinish?.();
    });

    it('does not reload superpixels again when saving a stroke', async () => {
        const rect = await renderReady('sample-no-reload');

        await stroke(rect, [{ x: 0, y: 0 }]);

        expect(loadSuperpixelsForImageMock).toHaveBeenCalledTimes(1);
    });
});
