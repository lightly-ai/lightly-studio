import { fireEvent, render } from '@testing-library/svelte';
import { tick } from 'svelte';
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import SamplePolygonRect from './SamplePolygonRect.svelte';

const {
    mockAnnotationContext,
    setAnnotationId,
    setIsDrawing,
    setAnnotationLabel,
    setLastCreatedAnnotationId,
    createAnnotationMock,
    deleteAnnotationMock,
    addReversibleActionMock,
    refetchRootCollectionMock
} = vi.hoisted(() => {
    const context = {
        annotationId: null as string | null,
        annotationType: 'polygon' as string | null,
        annotationLabel: null as string | null,
        annotationSource: null as string | null,
        isDrawing: false,
        isOnAnnotationDetailsView: false
    };

    const setAnnotationIdMock = vi.fn((id: string | null) => {
        context.annotationId = id;
    });
    const setIsDrawingMock = vi.fn((value: boolean) => {
        context.isDrawing = value;
    });
    const setAnnotationLabelMock = vi.fn((label: string | null) => {
        context.annotationLabel = label;
    });
    const setLastCreatedAnnotationIdMock = vi.fn();
    const createAnnotation = vi.fn().mockResolvedValue({ sample_id: 'new-polygon-id' });
    const deleteAnnotation = vi.fn().mockResolvedValue(undefined);
    const addReversibleAction = vi.fn();
    const refetchRootCollection = vi.fn();

    return {
        mockAnnotationContext: context,
        setAnnotationId: setAnnotationIdMock,
        setIsDrawing: setIsDrawingMock,
        setAnnotationLabel: setAnnotationLabelMock,
        setLastCreatedAnnotationId: setLastCreatedAnnotationIdMock,
        createAnnotationMock: createAnnotation,
        deleteAnnotationMock: deleteAnnotation,
        addReversibleActionMock: addReversibleAction,
        refetchRootCollectionMock: refetchRootCollection
    };
});

vi.mock('$app/state', () => ({
    page: {
        params: { dataset_id: 'dataset-1' }
    }
}));

vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({
        context: mockAnnotationContext,
        setIsDrawing,
        setAnnotationId,
        setAnnotationLabel,
        setLastCreatedAnnotationId
    })
}));

vi.mock('$lib/hooks/useAnnotationLabels/useAnnotationLabels', () => ({
    useAnnotationLabels: () => ({
        data: [{ annotation_label_id: 'label-1', annotation_label_name: 'car' }]
    })
}));

vi.mock('$lib/hooks/useSelectClassDialog/useSelectClassDialog', () => ({
    useSelectClassDialog: () => ({
        open: { subscribe: vi.fn(() => vi.fn()) },
        requestLabel: vi.fn().mockResolvedValue({ label: 'car' }),
        handleConfirm: vi.fn(),
        handleCancel: vi.fn()
    })
}));

vi.mock('$lib/hooks/useCreateAnnotation/useCreateAnnotation', () => ({
    useCreateAnnotation: () => ({
        createAnnotation: createAnnotationMock
    })
}));

vi.mock('$lib/hooks/useCreateLabel/useCreateLabel', () => ({
    useCreateLabel: () => ({
        createLabel: vi.fn().mockResolvedValue({
            annotation_label_id: 'label-1',
            annotation_label_name: 'car'
        })
    })
}));

vi.mock('$lib/hooks/useCollection/useCollection', () => ({
    useCollectionWithChildren: () => ({
        refetch: refetchRootCollectionMock
    })
}));

vi.mock('$lib/hooks/useDeleteAnnotation/useDeleteAnnotation', () => ({
    useDeleteAnnotation: () => ({
        deleteAnnotation: deleteAnnotationMock
    })
}));

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        addReversibleAction: addReversibleActionMock,
        updateLastAnnotationLabel: vi.fn()
    })
}));

vi.mock('$lib/services/addAnnotationCreateToUndoStack', () => ({
    addAnnotationCreateToUndoStack: vi.fn()
}));

vi.mock('svelte-sonner', () => ({
    toast: {
        success: vi.fn(),
        error: vi.fn()
    }
}));

vi.mock('$lib/components/SelectClassDialog/SelectClassDialog.svelte', () => ({
    default: vi.fn()
}));

const baseSample = {
    width: 200,
    height: 100,
    annotations: []
};

const baseProps = {
    sample: baseSample,
    sampleId: 'sample-1',
    collectionId: 'collection-1',
    drawerStrokeColor: 'rgb(0,123,255)',
    refetch: vi.fn()
};

// Simulate getBoundingClientRect for the SVG rect:
// canvas occupies [left=0, top=0, width=200, height=100] in screen space,
// matching the image dimensions for 1:1 coordinate mapping.
const mockRectBounds = {
    left: 0,
    top: 0,
    width: 200,
    height: 100,
    right: 200,
    bottom: 100
};

const mockBoundingClientRect = () => mockRectBounds as DOMRect;

describe('SamplePolygonRect', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockAnnotationContext.annotationId = null;
        mockAnnotationContext.annotationType = 'polygon';
        mockAnnotationContext.annotationLabel = 'car';
        mockAnnotationContext.isDrawing = false;
        createAnnotationMock.mockResolvedValue({ sample_id: 'new-polygon-id' });
        vi.spyOn(Element.prototype, 'getBoundingClientRect').mockImplementation(
            mockBoundingClientRect
        );
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    const clickAt = async (element: Element, clientX: number, clientY: number, detail = 1) => {
        await fireEvent(
            element,
            new MouseEvent('click', { bubbles: true, clientX, clientY, detail })
        );
        await tick();
    };

    const getInteractionRect = (container: HTMLElement): Element => {
        const rect = container.querySelector('rect');
        expect(rect).not.toBeNull();
        return rect as Element;
    };

    it('renders with a crosshair interaction rect', () => {
        const { container } = render(SamplePolygonRect, { props: baseProps });
        const rect = container.querySelector('rect');
        expect(rect).not.toBeNull();
        expect(rect?.getAttribute('style')).toContain('crosshair');
    });

    it('adds a vertex on each single click in image coordinates', async () => {
        const { container } = render(SamplePolygonRect, { props: baseProps });
        const rect = getInteractionRect(container);

        // Click at screen (50, 25) → image coords (50, 25) given 1:1 scale
        await clickAt(rect, 50, 25);
        await clickAt(rect, 100, 50);
        await clickAt(rect, 150, 75);

        // Three vertex circles should be visible
        const circles = container.querySelectorAll('circle');
        expect(circles).toHaveLength(3);

        // First circle at expected image coords
        expect(circles[0].getAttribute('cx')).toBe('50');
        expect(circles[0].getAttribute('cy')).toBe('25');
    });

    it('sets isDrawing=true on the first click', async () => {
        const { container } = render(SamplePolygonRect, { props: baseProps });
        const rect = getInteractionRect(container);

        await clickAt(rect, 10, 10);

        expect(setIsDrawing).toHaveBeenCalledWith(true);
    });

    it('clamps coordinates to image bounds', async () => {
        const { container } = render(SamplePolygonRect, { props: baseProps });
        const rect = getInteractionRect(container);

        // Click outside image bounds (beyond 200x100)
        await clickAt(rect, -10, -10);
        await clickAt(rect, 300, 200);
        await clickAt(rect, 100, 50);

        const circles = container.querySelectorAll('circle');
        expect(circles).toHaveLength(3);

        // Clamped to (0, 0)
        expect(circles[0].getAttribute('cx')).toBe('0');
        expect(circles[0].getAttribute('cy')).toBe('0');

        // Clamped to (200, 100)
        expect(circles[1].getAttribute('cx')).toBe('200');
        expect(circles[1].getAttribute('cy')).toBe('100');
    });

    it('does not submit when fewer than 3 points on Enter', async () => {
        const { container } = render(SamplePolygonRect, { props: baseProps });
        const rect = getInteractionRect(container);

        await clickAt(rect, 10, 10);
        await clickAt(rect, 20, 20);

        await fireEvent.keyDown(rect, { key: 'Enter' });
        await tick();

        expect(createAnnotationMock).not.toHaveBeenCalled();
    });

    it('submits polygon with 3+ points on Enter key', async () => {
        const { container } = render(SamplePolygonRect, { props: baseProps });
        const rect = getInteractionRect(container);

        await clickAt(rect, 10, 10);
        await clickAt(rect, 100, 10);
        await clickAt(rect, 55, 80);

        await fireEvent.keyDown(rect, { key: 'Enter' });
        await tick();

        expect(createAnnotationMock).toHaveBeenCalledWith(
            expect.objectContaining({
                annotation_type: 'polygon',
                parent_sample_id: 'sample-1',
                points: [
                    [10, 10],
                    [100, 10],
                    [55, 80]
                ]
            })
        );
    });

    it('cancels polygon draft on Escape key', async () => {
        const { container } = render(SamplePolygonRect, { props: baseProps });
        const rect = getInteractionRect(container);

        await clickAt(rect, 10, 10);
        await clickAt(rect, 50, 50);

        await fireEvent.keyDown(rect, { key: 'Escape' });
        await tick();

        const circles = container.querySelectorAll('circle');
        expect(circles).toHaveLength(0);
        expect(createAnnotationMock).not.toHaveBeenCalled();
        expect(setIsDrawing).toHaveBeenLastCalledWith(false);
    });

    it('submits polygon on double-click', async () => {
        const { container } = render(SamplePolygonRect, { props: baseProps });
        const rect = getInteractionRect(container);

        await clickAt(rect, 10, 10);
        await clickAt(rect, 100, 10);
        // Double-click: detail=1 adds the third point, detail=2 finishes
        await clickAt(rect, 55, 80, 1);
        await clickAt(rect, 55, 80, 2);
        await tick();

        expect(createAnnotationMock).toHaveBeenCalledWith(
            expect.objectContaining({
                annotation_type: 'polygon',
                points: expect.arrayContaining([[10, 10]])
            })
        );
    });

    it('clears draft state after successful submission', async () => {
        const { container } = render(SamplePolygonRect, { props: baseProps });
        const rect = getInteractionRect(container);

        await clickAt(rect, 10, 10);
        await clickAt(rect, 100, 10);
        await clickAt(rect, 55, 80);

        await fireEvent.keyDown(rect, { key: 'Enter' });
        await tick();
        // Wait for async createAnnotation promise
        await tick();

        const circles = container.querySelectorAll('circle');
        expect(circles).toHaveLength(0);
    });

    it('calls refetch and undo-stack after successful creation', async () => {
        const { addAnnotationCreateToUndoStack } = await import(
            '$lib/services/addAnnotationCreateToUndoStack'
        );
        const refetch = vi.fn();
        const { container } = render(SamplePolygonRect, {
            props: { ...baseProps, refetch }
        });
        const rect = getInteractionRect(container);

        await clickAt(rect, 10, 10);
        await clickAt(rect, 100, 10);
        await clickAt(rect, 55, 80);
        await fireEvent.keyDown(rect, { key: 'Enter' });
        await tick();
        await tick();

        expect(refetch).toHaveBeenCalled();
        expect(addAnnotationCreateToUndoStack).toHaveBeenCalled();
    });
});
