import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import FindInstancesOverlay from './FindInstancesOverlay.svelte';

const prediction = {
    bbox: { x: 10, y: 10, width: 20, height: 20 },
    segmentation_mask: [0, 1],
    score: null
};

const mocks = vi.hoisted(() => ({
    instances: {
        predictions: [] as unknown[],
        boxes: [] as { x: number; y: number; width: number; height: number }[],
        isSaving: false,
        addBox: vi.fn(),
        removePrediction: vi.fn()
    }
}));

const defaultProps = {
    sample: { width: 100, height: 100 },
    scale: 1,
    saveAs: 'box' as const,
    isDrawingBox: true,
    onBoxDrawn: vi.fn(),
    instances: mocks.instances as never
};

const getInteractionRect = (container: HTMLElement) => {
    const rect = container.querySelector<SVGRectElement>('rect[role="button"]');
    if (!rect) throw new Error('Missing interaction rect');
    rect.getBoundingClientRect = () => ({ left: 0, top: 0, width: 100, height: 100 }) as DOMRect;
    rect.setPointerCapture = vi.fn();
    rect.releasePointerCapture = vi.fn();
    return rect;
};

// jsdom has no PointerEvent, so a MouseEvent carries the button and position.
const firePointer = (rect: SVGRectElement, type: string, position: number) =>
    fireEvent(
        rect,
        new MouseEvent(type, { bubbles: true, button: 0, clientX: position, clientY: position })
    );

describe('FindInstancesOverlay', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mocks.instances.predictions = [];
        mocks.instances.boxes = [];
    });

    it('adds a drawn box and ends the drawing', async () => {
        const onBoxDrawn = vi.fn();
        const { container } = render(FindInstancesOverlay, {
            props: { ...defaultProps, onBoxDrawn }
        });
        const rect = getInteractionRect(container);

        await firePointer(rect, 'pointerdown', 10);
        await firePointer(rect, 'pointermove', 50);
        await firePointer(rect, 'pointerup', 50);

        expect(mocks.instances.addBox).toHaveBeenCalledWith({
            x: 0.1,
            y: 0.1,
            width: 0.4,
            height: 0.4
        });
        expect(onBoxDrawn).toHaveBeenCalledOnce();
    });

    it('ends the drawing when the pointer is cancelled', async () => {
        const onBoxDrawn = vi.fn();
        const { container } = render(FindInstancesOverlay, {
            props: { ...defaultProps, onBoxDrawn }
        });

        await fireEvent.pointerCancel(getInteractionRect(container));

        expect(mocks.instances.addBox).not.toHaveBeenCalled();
        expect(onBoxDrawn).toHaveBeenCalledOnce();
    });

    it('removes the instance of a clicked delete button', async () => {
        mocks.instances.predictions = [prediction];
        mocks.instances.boxes = [{ x: 0.1, y: 0.1, width: 0.2, height: 0.2 }];
        render(FindInstancesOverlay, { props: { ...defaultProps, isDrawingBox: false } });

        await fireEvent.click(screen.getByRole('button', { name: 'Delete instance 1' }));

        expect(mocks.instances.removePrediction).toHaveBeenCalledWith(prediction);
    });
});
