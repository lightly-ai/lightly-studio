import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { AnnotationView } from '$lib/api/lightly_studio_local';
import type { ComponentProps } from 'svelte';
import SampleSlicRect from './SampleSlicRect.svelte';
import { toast } from 'svelte-sonner';

const {
    mockAnnotationContext,
    mockToolbarContext,
    finishBrushMock,
    loadSuperpixelsForImageMock,
    setAnnotationIdMock,
    setIsDrawingMock,
    updateAnnotationMock,
    getImageCoordsFromMouseMock
} = vi.hoisted(() => {
    const annotationContext = {
        annotationId: null as string | null,
        isDrawing: false,
        isOnAnnotationDetailsView: false,
        lockedAnnotationIds: new Set<string>(),
        isAnnotationLocked: () => false
    };
    const toolbarContext = {
        status: 'slic' as const,
        slic: {
            level: 'medium' as 'coarse' | 'medium' | 'fine',
            status: 'idle' as 'idle' | 'computing' | 'ready' | 'error'
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
        getImageCoordsFromMouseMock: () => ({ x: 1, y: 0 })
    };
});

vi.mock('$app/state', () => ({
    page: { params: { dataset_id: 'dataset-1' } }
}));

vi.mock('$lib/components/SampleAnnotation/utils', async (importOriginal) => ({
    decodeRLEToBinaryMask: (
        await importOriginal<typeof import('$lib/components/SampleAnnotation/utils')>()
    ).decodeRLEToBinaryMask,
    getImageCoordsFromMouse: getImageCoordsFromMouseMock,
    maskToDataUrl: () => 'data:image/png;base64,mock'
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

vi.mock('$lib/hooks', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/hooks')>()),
    useAnnotation: () => ({ updateAnnotation: updateAnnotationMock }),
    useAnnotationLabels: () => ({ data: [] }),
    useDeleteAnnotation: () => ({ deleteAnnotation: vi.fn() }),
    useCollectionWithChildren: () => ({ refetch: vi.fn() }),
    useSegmentationMaskBrush: () => ({ finishBrush: finishBrushMock }),
    useSelectClassDialog: () => ({
        open: writable(false),
        requestLabel: vi.fn(),
        handleConfirm: vi.fn(),
        handleCancel: vi.fn()
    })
}));

vi.mock('$lib/utils/slic', () => ({
    loadSuperpixelsForImage: loadSuperpixelsForImageMock
}));

const defaultProps: ComponentProps<typeof SampleSlicRect> = {
    sample: { width: 3, height: 1, annotations: [] },
    sampleId: 'sample-1',
    collectionId: 'collection-1',
    drawerStrokeColor: 'rgb(0, 0, 255)',
    imageUrl: 'https://example.com/image.png',
    refetch: vi.fn()
};

const selectedAnnotation: AnnotationView = {
    sample_id: 'annotation-1',
    annotation_type: 'segmentation_mask',
    parent_sample_id: 'sample-1',
    annotation_collection_id: 'collection-1',
    annotation_label: { annotation_label_name: 'Car' },
    created_at: new Date(0),
    segmentation_details: { x: 0, y: 0, width: 3, height: 1, segmentation_mask: [0, 1, 2] }
};

const renderReady = async (props: Partial<typeof defaultProps> = {}) => {
    const view = render(SampleSlicRect, { props: { ...defaultProps, ...props } });
    await waitFor(() => expect(mockToolbarContext.slic.status).toBe('ready'));

    return { rect: view.getByRole('button') };
};

const stroke = async (rect: Element) => {
    await fireEvent.pointerDown(rect, { pointerId: 1 });
    await fireEvent.pointerUp(rect, { pointerId: 1 });
};

describe('SampleSlicRect', () => {
    afterEach(() => vi.restoreAllMocks());
    beforeEach(() => {
        vi.clearAllMocks();
        mockAnnotationContext.annotationId = null;
        mockAnnotationContext.isDrawing = false;
        mockAnnotationContext.lockedAnnotationIds = new Set<string>();
        mockToolbarContext.slic.level = 'medium';
        mockToolbarContext.slic.status = 'idle';
        finishBrushMock.mockResolvedValue(undefined);
    });

    it('commits the editor mask through the brush persistence flow', async () => {
        const { rect } = await renderReady();
        await stroke(rect);

        expect(setIsDrawingMock).toHaveBeenCalledWith(true);
        expect(Array.from(finishBrushMock.mock.calls[0][0] as Uint8Array)).toEqual([0, 1, 0]);
    });

    it('reports save failures and allows another stroke', async () => {
        const error = new Error('Save failed');
        const log = vi.spyOn(console, 'error').mockImplementation(() => {});
        const notification = vi.spyOn(toast, 'error').mockImplementation(() => 'error-toast');
        const onFinishBrushPendingChange = vi.fn();
        finishBrushMock.mockRejectedValueOnce(error);
        const { rect } = await renderReady({ onFinishBrushPendingChange });
        await stroke(rect);
        await waitFor(() => {
            expect(log).toHaveBeenCalledWith('AI-assisted labeling save failed', error);
            expect(notification).toHaveBeenCalledWith('Could not save the segmentation annotation');
            expect(onFinishBrushPendingChange).toHaveBeenLastCalledWith({
                operation: expect.any(String),
                isPending: false
            });
        });
        await stroke(rect);
        expect(finishBrushMock).toHaveBeenCalledTimes(2);
    });

    it('cancels a stroke without saving a mask', async () => {
        const { rect } = await renderReady();
        await fireEvent.pointerDown(rect, { pointerId: 1 });
        await fireEvent.pointerCancel(rect, { pointerId: 1 });
        await fireEvent.pointerUp(rect, { pointerId: 1 });
        expect(finishBrushMock).not.toHaveBeenCalled();
        expect(mockAnnotationContext.isDrawing).toBe(false);
    });

    it('preserves an existing mask when adding another superpixel', async () => {
        mockAnnotationContext.annotationId = 'annotation-1';
        const { rect } = await renderReady({
            sample: { width: 3, height: 1, annotations: [selectedAnnotation] }
        });
        await stroke(rect);
        expect(Array.from(finishBrushMock.mock.calls[0][0] as Uint8Array)).toEqual([1, 1, 0]);
        expect(finishBrushMock.mock.calls[0][1]).toEqual(selectedAnnotation);
    });
});
