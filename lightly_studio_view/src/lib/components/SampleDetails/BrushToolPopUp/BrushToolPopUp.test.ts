import { render, fireEvent, getByLabelText, queryByLabelText } from '@testing-library/svelte';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import BrushTool from './BrushToolPopUp.svelte';
import { BrushMode } from '$lib/contexts/SampleDetailsToolbar.svelte';

let mockContext: {
    brush: {
        mode: 'brush' | 'eraser';
        size: number;
    };
};

const mockAnnotationLabelContext = {
    annotationLabel: null as string | null,
    annotationId: null as string | null,
    lastCreatedAnnotationId: null as string | null,
    isDrawing: false,
    isErasing: false,
    isAnnotationDetails: false
};

vi.mock('$lib/contexts/SampleDetailsToolbar.svelte', () => {
    return {
        useSampleDetailsToolbarContext: () => ({
            context: mockContext,
            setBrushMode: (value: BrushMode) => {
                mockContext.brush.mode = value;
            }
        })
    };
});

vi.mock('$lib/contexts/SampleDetailsAnnotation.svelte', () => ({
    useAnnotationLabelContext: () => ({
        context: mockAnnotationLabelContext,
        setAnnotationId(id: string | null) {
            mockAnnotationLabelContext.annotationId = id;
        },
        setLastCreatedAnnotationId(id: string | null) {
            mockAnnotationLabelContext.lastCreatedAnnotationId = id;
        }
    })
}));

describe('BrushTool component', () => {
    beforeEach(() => {
        mockContext = {
            brush: {
                mode: 'brush',
                size: 10
            }
        };
    });

    it('switches to eraser mode when eraser button is clicked', async () => {
        const { container } = render(BrushTool);

        const eraserButton = getByLabelText(container, 'Eraser mode');

        await fireEvent.click(eraserButton);

        expect(mockContext.brush.mode).toBe('eraser');
    });

    it('switches back to brush mode when brush button is clicked', async () => {
        const { container } = render(BrushTool);

        const brushButton = getByLabelText(container, 'Brush mode');

        await fireEvent.click(brushButton);

        expect(mockContext.brush.mode).toBe('brush');
    });

    it('updates brush size when slider changes', async () => {
        const { getByRole } = render(BrushTool);

        const slider = getByRole('slider') as HTMLInputElement;

        await fireEvent.input(slider, { target: { value: '42' } });

        expect(mockContext.brush.size).toBe(42);
    });

    it('finishes instance', async () => {
        const { container } = render(BrushTool);

        const finishButton = getByLabelText(container, 'Finish instance');
        await fireEvent.click(finishButton);

        expect(mockAnnotationLabelContext.annotationId).toBeNull();
        expect(mockAnnotationLabelContext.lastCreatedAnnotationId).toBeNull();
    });

    it('finishes instance button is hidden when is annotation details', async () => {
        mockAnnotationLabelContext.isAnnotationDetails = true;
        const { container } = render(BrushTool);

        const finishButton = queryByLabelText(container, 'Finish instance');

        expect(finishButton).toBeNull();
    });
});
