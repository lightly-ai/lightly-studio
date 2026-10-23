import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { ComponentProps } from 'svelte';
import { writable } from 'svelte/store';
import FindInstancesOverlay from './FindInstancesOverlay.svelte';

const prediction = {
    bbox: { x: 10, y: 10, width: 20, height: 20 },
    segmentation_mask: [0, 1],
    score: null
};

type Instances = ComponentProps<typeof FindInstancesOverlay>['instances'];

const mocks = vi.hoisted(() => ({
    instances: {
        predictions: [] as Instances['predictions'],
        boxes: [] as Instances['boxes'],
        isSaving: false,
        addBox: vi.fn(),
        removePrediction: vi.fn()
    }
}));

vi.mock('$lib/hooks/useSettings', () => ({
    useSettings: () => ({ settingsStore: writable({ key_go_back: 'Escape' }) })
}));

const defaultProps = {
    sample: { width: 100, height: 100 },
    scale: 1,
    isPanning: false,
    saveAs: 'box' as const,
    isDrawingBox: true,
    onDrawEnd: vi.fn(),
    // Only the fields the overlay reads.
    instances: mocks.instances as unknown as Instances
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
        mocks.instances.isSaving = false;
    });

    it('adds a drawn box and ends the drawing', async () => {
        const onDrawEnd = vi.fn();
        const { container } = render(FindInstancesOverlay, {
            props: { ...defaultProps, onDrawEnd }
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
        expect(onDrawEnd).toHaveBeenCalledOnce();
    });

    it('ends the drawing when the pointer is cancelled', async () => {
        const onDrawEnd = vi.fn();
        const { container } = render(FindInstancesOverlay, {
            props: { ...defaultProps, onDrawEnd }
        });

        await fireEvent.pointerCancel(getInteractionRect(container));

        expect(mocks.instances.addBox).not.toHaveBeenCalled();
        expect(onDrawEnd).toHaveBeenCalledOnce();
    });

    it('keeps drawing after a click without a drag', async () => {
        const onDrawEnd = vi.fn();
        const { container } = render(FindInstancesOverlay, {
            props: { ...defaultProps, onDrawEnd }
        });
        const rect = getInteractionRect(container);

        await firePointer(rect, 'pointerdown', 10);
        await firePointer(rect, 'pointerup', 10);

        expect(mocks.instances.addBox).not.toHaveBeenCalled();
        expect(onDrawEnd).not.toHaveBeenCalled();
    });

    it('keeps drawing after a right-click', async () => {
        const onDrawEnd = vi.fn();
        const { container } = render(FindInstancesOverlay, {
            props: { ...defaultProps, onDrawEnd }
        });
        const rect = getInteractionRect(container);

        await fireEvent(rect, new MouseEvent('pointerdown', { bubbles: true, button: 2 }));
        await firePointer(rect, 'pointerup', 50);

        expect(onDrawEnd).not.toHaveBeenCalled();
    });

    it('ends the drawing on Escape and keeps the tool open', async () => {
        const onDrawEnd = vi.fn();
        const onWindowKeyDown = vi.fn();
        window.addEventListener('keydown', onWindowKeyDown);
        render(FindInstancesOverlay, { props: { ...defaultProps, onDrawEnd } });

        await fireEvent.keyDown(document.body, { key: 'Escape' });

        expect(onDrawEnd).toHaveBeenCalledOnce();
        expect(onWindowKeyDown).not.toHaveBeenCalled();
        window.removeEventListener('keydown', onWindowKeyDown);
    });

    it('lets Escape through when not drawing', async () => {
        const onDrawEnd = vi.fn();
        const onWindowKeyDown = vi.fn();
        window.addEventListener('keydown', onWindowKeyDown);
        render(FindInstancesOverlay, {
            props: { ...defaultProps, isDrawingBox: false, onDrawEnd }
        });

        await fireEvent.keyDown(document.body, { key: 'Escape' });

        expect(onDrawEnd).not.toHaveBeenCalled();
        expect(onWindowKeyDown).toHaveBeenCalledOnce();
        window.removeEventListener('keydown', onWindowKeyDown);
    });

    it('lets pan events through while panning', () => {
        const { container } = render(FindInstancesOverlay, {
            props: { ...defaultProps, isPanning: true }
        });

        expect(getInteractionRect(container)).toHaveAttribute('pointer-events', 'none');
    });

    it('removes the instance of a clicked delete button', async () => {
        mocks.instances.predictions = [prediction];
        mocks.instances.boxes = [{ x: 0.1, y: 0.1, width: 0.2, height: 0.2 }];
        render(FindInstancesOverlay, { props: { ...defaultProps, isDrawingBox: false } });

        await fireEvent.click(screen.getByRole('button', { name: 'Delete instance 1' }));

        expect(mocks.instances.removePrediction).toHaveBeenCalledWith(prediction);
    });

    it('disables the delete buttons while saving', () => {
        mocks.instances.predictions = [prediction];
        mocks.instances.isSaving = true;
        render(FindInstancesOverlay, { props: { ...defaultProps, isDrawingBox: false } });

        expect(screen.getByRole('button', { name: 'Delete instance 1' })).toHaveAttribute(
            'aria-disabled',
            'true'
        );
    });
});
