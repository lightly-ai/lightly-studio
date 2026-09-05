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
    maskToDataUrlMock,
    queuedPoints
} = vi.hoisted(() => {
    const annotationContext = {
        annotationId: null as string | null,
        isDrawing: false,
        isOnAnnotationDetailsView: false,
        lockedAnnotationIds: new Set<string>(),
        isAnnotationLocked(annotationId: string) {
            return this.lockedAnnotationIds.has(annotationId);
        }
    };
    const toolbarContext = {
        status: 'slic' as const,
        slic: {
            level: 'medium' as 'coarse' | 'medium' | 'fine',
            status: 'idle' as 'idle' | 'computing' | 'ready' | 'error',
            retryCount: 0
        }
    };
    const createResult = () => ({
        segmentation: {
            labels: new Int32Array([0, 1, 2]),
            width: 3,
            height: 1,
            boundaries: new Uint8Array([1, 1, 1]),
            pixelIndexes: new Uint32Array([0, 1, 2]),
            segmentOffsets: new Uint32Array([0, 1, 2, 3]),
            labelPixelIndexes: [[0], [1], [2]],
            segmentCount: 3
        },
        sourceWidth: 3,
        sourceHeight: 1,
        scaleX: 1,
        scaleY: 1,
        level: 'medium'
    });

    return {
        mockAnnotationContext: annotationContext,
        mockToolbarContext: toolbarContext,
        finishBrushMock: vi.fn(),
        loadSuperpixelsForImageMock: vi.fn(async () => createResult()),
        setAnnotationIdMock: vi.fn((id: string | null) => {
            annotationContext.annotationId = id;
        }),
        setIsDrawingMock: vi.fn((value: boolean) => {
            annotationContext.isDrawing = value;
        }),
        updateAnnotationMock: vi.fn(),
        maskToDataUrlMock: vi.fn(() => 'data:image/png;base64,mock'),
        queuedPoints: [] as { x: number; y: number }[],
        getImageCoordsFromMouseMock: vi.fn(() => queuedPoints.shift() ?? { x: 0, y: 0 })
    };
});

vi.mock('$app/state', () => ({
    page: { params: { dataset_id: 'dataset-1' } }
}));

vi.mock('$lib/components/SampleAnnotation/utils', () => ({
    decodeRLEToBinaryMask: vi.fn(() => new Uint8Array([0, 0, 0])),
    getImageCoordsFromMouse: getImageCoordsFromMouseMock,
    maskToDataUrl: maskToDataUrlMock
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
    useAnnotation: () => ({ updateAnnotation: updateAnnotationMock })
}));

vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: () => ({ data: [] })
}));

vi.mock('$lib/hooks/useDeleteAnnotation/useDeleteAnnotation', () => ({
    useDeleteAnnotation: () => ({ deleteAnnotation: vi.fn() })
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
    useCollectionWithChildren: () => ({ refetch: vi.fn() })
}));

vi.mock('$lib/hooks/useSegmentationMaskBrush', () => ({
    useSegmentationMaskBrush: () => ({ finishBrush: finishBrushMock })
}));

vi.mock('$lib/utils/slic', () => ({
    loadSuperpixelsForImage: loadSuperpixelsForImageMock
}));

const defaultProps = {
    sample: { width: 3, height: 1, annotations: [] },
    sampleId: 'sample-1',
    collectionId: 'collection-1',
    drawerStrokeColor: 'rgb(0, 0, 255)',
    imageUrl: 'https://example.com/image.png',
    refetch: vi.fn()
};

const renderReady = async (props: Partial<typeof defaultProps> = {}) => {
    const view = render(SampleSlicRect, { props: { ...defaultProps, ...props } });
    await waitFor(() => expect(mockToolbarContext.slic.status).toBe('ready'));

    const rect = view.container.querySelector('rect');
    expect(rect).not.toBeNull();
    return { ...view, rect: rect as SVGRectElement };
};

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
        mockToolbarContext.slic.retryCount = 0;
        queuedPoints.length = 0;
        finishBrushMock.mockResolvedValue(undefined);
        getImageCoordsFromMouseMock.mockImplementation(
            () => queuedPoints.shift() ?? { x: 0, y: 0 }
        );
    });

    it('renders boundaries after loading superpixels', async () => {
        const { container } = await renderReady();
        expect(container.querySelectorAll('image')).toHaveLength(1);
        expect(loadSuperpixelsForImageMock).toHaveBeenCalledWith({
            imageUrl: defaultProps.imageUrl,
            level: 'medium'
        });
    });

    it('exposes an error state when superpixel loading fails', async () => {
        loadSuperpixelsForImageMock.mockRejectedValueOnce(new Error('compute failed'));
        render(SampleSlicRect, { props: defaultProps });
        await waitFor(() => expect(mockToolbarContext.slic.status).toBe('error'));
    });

    it('renders hover and stroke previews', async () => {
        const { container, rect } = await renderReady();
        queuedPoints.push({ x: 1, y: 0 });
        await fireEvent.pointerMove(rect);
        expect(container.querySelectorAll('image')).toHaveLength(2);

        queuedPoints.push({ x: 1, y: 0 }, { x: 2, y: 0 });
        await fireEvent.pointerDown(rect, { pointerId: 1 });
        await fireEvent.pointerMove(rect, { pointerId: 1 });
        expect(maskToDataUrlMock).toHaveBeenCalled();
        expect(container.querySelectorAll('image').length).toBeGreaterThanOrEqual(2);
    });

    it('commits the editor mask through the brush persistence flow', async () => {
        const { rect } = await renderReady();
        await stroke(rect, [{ x: 1, y: 0 }]);

        expect(setIsDrawingMock).toHaveBeenCalledWith(true);
        expect(Array.from(finishBrushMock.mock.calls[0][0] as Uint8Array)).toEqual([0, 1, 0]);
    });

    it('blocks editing locked annotations', async () => {
        mockAnnotationContext.annotationId = 'annotation-1';
        mockAnnotationContext.lockedAnnotationIds.add('annotation-1');
        const annotation = {
            sample_id: 'annotation-1',
            annotation_type: 'segmentation_mask',
            segmentation_details: { segmentation_mask: [3] }
        };
        const { rect } = await renderReady({
            sample: { width: 3, height: 1, annotations: [annotation] } as typeof defaultProps.sample
        });

        await stroke(rect, [{ x: 1, y: 0 }]);
        expect(finishBrushMock).not.toHaveBeenCalled();
    });

    it('blocks a new stroke while a save is in flight', async () => {
        let resolveFinish: (() => void) | undefined;
        finishBrushMock.mockImplementation(
            () => new Promise<void>((resolve) => (resolveFinish = resolve))
        );
        const { rect } = await renderReady();

        await stroke(rect, [{ x: 0, y: 0 }]);
        await stroke(rect, [{ x: 1, y: 0 }], 2);
        expect(finishBrushMock).toHaveBeenCalledTimes(1);
        resolveFinish?.();
    });

    it('loads the selected level and recomputes when the image changes', async () => {
        mockToolbarContext.slic.level = 'fine';
        const { rerender } = await renderReady();
        expect(loadSuperpixelsForImageMock).toHaveBeenLastCalledWith({
            imageUrl: defaultProps.imageUrl,
            level: 'fine'
        });

        await rerender({ ...defaultProps, imageUrl: 'https://example.com/next.png' });
        await waitFor(() => expect(loadSuperpixelsForImageMock).toHaveBeenCalledTimes(2));
        expect(loadSuperpixelsForImageMock).toHaveBeenLastCalledWith({
            imageUrl: 'https://example.com/next.png',
            level: 'fine'
        });
    });
});
