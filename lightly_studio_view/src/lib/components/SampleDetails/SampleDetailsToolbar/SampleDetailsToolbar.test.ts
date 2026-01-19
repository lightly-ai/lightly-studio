import { render, fireEvent } from '@testing-library/svelte';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import SampleDetailsToolbar from './SampleDetailsToolbar.svelte';
import { AnnotationType } from '$lib/api/lightly_studio_local';
import { BrushMode, ToolbarStatus } from '$lib/contexts/SampleDetailsToolbar.svelte';

const mockSampleDetailsToolbarContext = {
    status: 'cursor' as 'cursor' | 'bounding-box' | 'brush',
    brush: {
        mode: 'brush' as 'brush' | 'eraser'
    }
};

const mockAnnotationLabelContext = {
    annotationType: null as AnnotationType | null,
    annotationLabel: null as string | null,
    annotationId: null as string | null,
    lastCreatedAnnotationId: null as string | null,
    isDrawing: false,
    isErasing: false
};

vi.mock('$lib/contexts/SampleDetailsToolbar.svelte', () => ({
    useSampleDetailsToolbarContext: () => ({
        context: mockSampleDetailsToolbarContext,
        setBrushMode(mode: BrushMode) {
            mockSampleDetailsToolbarContext.brush.mode = mode;
        },
        setStatus(status: ToolbarStatus) {
            mockSampleDetailsToolbarContext.status = status;
        }
    })
}));

vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({
        context: mockAnnotationLabelContext,
        setAnnotationId(id: string | null) {
            mockAnnotationLabelContext.annotationId = id;
        },
        setAnnotationLabel(label: string | null) {
            mockAnnotationLabelContext.annotationLabel = label;
        },
        setLastCreatedAnnotationId(id: string | null) {
            mockAnnotationLabelContext.lastCreatedAnnotationId = id;
        },
        setIsDrawing(value: boolean) {
            mockAnnotationLabelContext.isDrawing = value;
        },
        setIsErasing(value: boolean) {
            mockAnnotationLabelContext.isErasing = value;
        },
        setAnnotationType(value: AnnotationType) {
            mockAnnotationLabelContext.annotationType = value;
        }
    })
}));

describe('SampleDetailsToolbar', () => {
    beforeEach(() => {
        mockSampleDetailsToolbarContext.status = 'cursor';
        mockSampleDetailsToolbarContext.brush.mode = 'brush';

        mockAnnotationLabelContext.annotationType = null;
        mockAnnotationLabelContext.annotationLabel = null;
        mockAnnotationLabelContext.annotationId = null;
        mockAnnotationLabelContext.lastCreatedAnnotationId = null;
        mockAnnotationLabelContext.isDrawing = false;
        mockAnnotationLabelContext.isErasing = false;
    });

    it('starts in cursor mode and resets annotation state on mount', () => {
        mockAnnotationLabelContext.annotationLabel = 'car';
        mockAnnotationLabelContext.annotationId = 'id-1';
        mockAnnotationLabelContext.lastCreatedAnnotationId = 'id-2';

        render(SampleDetailsToolbar);

        expect(mockSampleDetailsToolbarContext.status).toBe('cursor');
        expect(mockAnnotationLabelContext.annotationLabel).toBe('car');
        expect(mockAnnotationLabelContext.annotationId).toBeNull();
        expect(mockAnnotationLabelContext.lastCreatedAnnotationId).toBeNull();
        expect(mockAnnotationLabelContext.annotationType).toBeNull();
    });

    it('activates bounding box tool and sets annotation type', async () => {
        mockAnnotationLabelContext.annotationLabel = 'car';
        const { getByLabelText } = render(SampleDetailsToolbar);

        await fireEvent.click(getByLabelText('Bounding Box Tool'));

        expect(mockSampleDetailsToolbarContext.status).toBe('bounding-box');
        expect(mockAnnotationLabelContext.annotationType).toBe(AnnotationType.OBJECT_DETECTION);
        expect(mockAnnotationLabelContext.annotationLabel).toBe('car');
        expect(mockAnnotationLabelContext.annotationId).toBeNull();
    });

    it('toggles bounding box tool back to cursor when already focused', async () => {
        mockSampleDetailsToolbarContext.status = 'bounding-box';
        mockAnnotationLabelContext.annotationLabel = 'car';

        mockAnnotationLabelContext.annotationType = AnnotationType.OBJECT_DETECTION;

        const { getByLabelText } = render(SampleDetailsToolbar);

        mockSampleDetailsToolbarContext.status = 'bounding-box';

        await fireEvent.click(getByLabelText('Bounding Box Tool'));

        expect(mockSampleDetailsToolbarContext.status).toBe('cursor');
        expect(mockAnnotationLabelContext.annotationType).toBeNull();
    });

    it('activates brush tool and sets instance segmentation', async () => {
        mockAnnotationLabelContext.annotationLabel = 'car';
        const { getByLabelText } = render(SampleDetailsToolbar);

        await fireEvent.click(getByLabelText('Brush Tool'));

        expect(mockSampleDetailsToolbarContext.status).toBe('brush');
        expect(mockAnnotationLabelContext.annotationType).toBe(
            AnnotationType.INSTANCE_SEGMENTATION
        );
        expect(mockAnnotationLabelContext.annotationLabel).toBe('car');
        expect(mockAnnotationLabelContext.annotationId).toBeNull();
    });

    it('switching to cursor resets drawing and erasing flags', async () => {
        mockSampleDetailsToolbarContext.status = 'brush';
        mockAnnotationLabelContext.isDrawing = true;
        mockAnnotationLabelContext.isErasing = true;
        mockAnnotationLabelContext.annotationLabel = 'car';

        const { getByLabelText } = render(SampleDetailsToolbar);

        await fireEvent.click(getByLabelText('Cursor Tool'));

        // Force reload
        render(SampleDetailsToolbar);

        expect(mockSampleDetailsToolbarContext.status).toBe('cursor');
        expect(mockAnnotationLabelContext.isDrawing).toBe(false);
        expect(mockAnnotationLabelContext.isErasing).toBe(false);
        expect(mockAnnotationLabelContext.annotationLabel).toBe('car');
    });
});
