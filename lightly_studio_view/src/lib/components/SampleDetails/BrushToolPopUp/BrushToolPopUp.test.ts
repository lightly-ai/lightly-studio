import { render, fireEvent, getByLabelText, queryByLabelText } from '@testing-library/svelte';
import { writable } from 'svelte/store';
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
    isChangingBrushSize: false,
    isOnAnnotationDetailsView: false
};

const settingsStore = writable({
    key_toolbar_brush: 'r',
    key_toolbar_eraser: 'x'
});

vi.mock('$lib/hooks/useSettings', () => ({
    useSettings: () => ({
        settingsStore
    })
}));

vi.mock('$lib/contexts/SampleDetailsToolbar.svelte', () => {
    return {
        useSampleDetailsToolbarContext: () => ({
            context: mockContext,
            setBrushMode: (value: BrushMode) => {
                mockContext.brush.mode = value;
            },
            setBrushSize: (value: number) => {
                mockContext.brush.size = value;
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
        },
        setIsChangingBrushSize(value: boolean) {
            mockAnnotationLabelContext.isChangingBrushSize = value;
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
        mockAnnotationLabelContext.annotationId = null;
        mockAnnotationLabelContext.lastCreatedAnnotationId = null;
        mockAnnotationLabelContext.isChangingBrushSize = false;
        mockAnnotationLabelContext.isOnAnnotationDetailsView = false;
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

    it('increases brush size when pressing Alt and scrolling up', async () => {
        render(BrushTool);

        await fireEvent.wheel(window, { deltaY: -100, altKey: true });

        expect(mockContext.brush.size).toBe(11);
    });

    it('decreases brush size when pressing Alt and scrolling down', async () => {
        render(BrushTool);

        await fireEvent.wheel(window, { deltaY: 100, altKey: true });

        expect(mockContext.brush.size).toBe(9);
    });

    it('updates brush size when pressing Alt and scrolling outside the popup', async () => {
        render(BrushTool);

        await fireEvent.wheel(document.body, { deltaY: -100, altKey: true });

        expect(mockContext.brush.size).toBe(11);
    });

    it('toggles changing brush size flag while handling Alt + wheel', async () => {
        vi.useFakeTimers();
        try {
            render(BrushTool);

            await fireEvent.wheel(window, { deltaY: -100, altKey: true });
            expect(mockAnnotationLabelContext.isChangingBrushSize).toBe(true);

            vi.advanceTimersByTime(100);
            expect(mockAnnotationLabelContext.isChangingBrushSize).toBe(false);
        } finally {
            vi.useRealTimers();
        }
    });

    it('keeps brush size within min/max bounds when pressing Alt and scrolling', async () => {
        render(BrushTool);

        mockContext.brush.size = 1;
        await fireEvent.wheel(window, { deltaY: 100, altKey: true });
        expect(mockContext.brush.size).toBe(1);

        mockContext.brush.size = 100;
        await fireEvent.wheel(window, { deltaY: -100, altKey: true });
        expect(mockContext.brush.size).toBe(100);
    });

    it('does not update brush size when Alt is not pressed', async () => {
        render(BrushTool);

        await fireEvent.wheel(window, { deltaY: -100 });

        expect(mockContext.brush.size).toBe(10);
    });

    it('does not update brush size when wheel target is an input element', async () => {
        const { getByRole } = render(BrushTool);
        const slider = getByRole('slider');

        await fireEvent.wheel(slider, { deltaY: -100, altKey: true });

        expect(mockContext.brush.size).toBe(10);
    });

    it('switches to eraser mode when eraser shortcut is pressed', async () => {
        render(BrushTool);

        await fireEvent.keyDown(window, { key: 'x' });

        expect(mockContext.brush.mode).toBe('eraser');
    });

    it('switches to brush mode when brush shortcut is pressed', async () => {
        mockContext.brush.mode = 'eraser';
        render(BrushTool);

        await fireEvent.keyDown(window, { key: 'r' });

        expect(mockContext.brush.mode).toBe('brush');
    });

    it('completes the editing by click', async () => {
        const { container } = render(BrushTool);

        const finishButton = getByLabelText(container, 'Finish');
        await fireEvent.click(finishButton);

        expect(mockAnnotationLabelContext.annotationId).toBeNull();
        expect(mockAnnotationLabelContext.lastCreatedAnnotationId).toBeNull();
    });

    it('hides the Finish button on annotation details view', async () => {
        mockAnnotationLabelContext.isOnAnnotationDetailsView = true;
        const { container } = render(BrushTool);

        const finishButton = queryByLabelText(container, 'Finish');

        expect(finishButton).toBeNull();
    });
});
