import { render, fireEvent, getByLabelText } from '@testing-library/svelte';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import BrushTool from './BrushToolPopUp.svelte';
import { BrushMode } from '$lib/contexts/SampleDetailsToolbar.svelte';

let mockContext: {
    brush: {
        mode: 'brush' | 'eraser';
        size: number;
    };
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
});
