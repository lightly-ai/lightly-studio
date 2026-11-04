import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import ResizableRectangle from './ResizableRectangle.svelte';

const renderRectangle = () => {
    const callbacks = { onDragStart: vi.fn(), onDragStop: vi.fn(), onDragEnd: vi.fn() };
    render(ResizableRectangle, {
        props: { bbox: { x: 10, y: 10, width: 40, height: 40 }, ...callbacks }
    });
    return callbacks;
};

// d3-drag reads `event.view`, which jsdom does not fill in for dispatched events.
const mouseEvent = (type: string, target: EventTarget) => {
    const event = new MouseEvent(type, { bubbles: true, button: 0, clientX: 20, clientY: 20 });
    Object.defineProperty(event, 'view', { value: window });
    target.dispatchEvent(event);
};

describe('ResizableRectangle', () => {
    it('signals the start and the stop of a move, even when nothing moved', async () => {
        const { onDragStart, onDragStop, onDragEnd } = renderRectangle();

        mouseEvent('mousedown', await screen.findByTestId('annotation_box'));
        expect(onDragStart).toHaveBeenCalledOnce();
        expect(onDragStop).not.toHaveBeenCalled();
        mouseEvent('mouseup', window);

        expect(onDragStop).toHaveBeenCalledOnce();
        expect(onDragEnd).not.toHaveBeenCalled();
    });

    it('signals the start of a resize', async () => {
        const { onDragStart } = renderRectangle();

        mouseEvent('mousedown', await screen.findByTestId('resize-handle-se'));

        expect(onDragStart).toHaveBeenCalledOnce();
    });
});
