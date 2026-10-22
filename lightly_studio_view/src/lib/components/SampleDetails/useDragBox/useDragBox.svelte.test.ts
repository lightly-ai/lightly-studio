import { describe, expect, it, vi } from 'vitest';
import { useDragBox } from './useDragBox.svelte';

const rect = { left: 0, top: 0, width: 100, height: 100 };

const pointerEvent = ({ x, y, button = 0 }: { x: number; y: number; button?: number }) =>
    ({
        clientX: x,
        clientY: y,
        button,
        pointerId: 1,
        currentTarget: { setPointerCapture: vi.fn(), releasePointerCapture: vi.fn() }
    }) as unknown as PointerEvent & { currentTarget: SVGRectElement };

const setup = () =>
    useDragBox(() => ({
        interactionRect: { getBoundingClientRect: () => rect } as unknown as SVGRectElement
    }));

describe('useDragBox', () => {
    it('returns the start point for a click', () => {
        const drag = setup();

        drag.onPointerDown(pointerEvent({ x: 50, y: 25 }));

        expect(drag.onPointerUp(pointerEvent({ x: 50, y: 25 }))).toEqual({
            start: { x: 0.5, y: 0.25 },
            box: null
        });
    });

    it('returns the box for a drag', () => {
        const drag = setup();

        drag.onPointerDown(pointerEvent({ x: 10, y: 10 }));
        drag.onPointerMove(pointerEvent({ x: 60, y: 60 }));

        expect(drag.onPointerUp(pointerEvent({ x: 60, y: 60 }))).toEqual({
            start: { x: 0.1, y: 0.1 },
            box: { x: 0.1, y: 0.1, width: 0.5, height: 0.5 }
        });
    });

    it('ignores buttons other than the primary one', () => {
        const drag = setup();

        drag.onPointerDown(pointerEvent({ x: 10, y: 10, button: 2 }));
        drag.onPointerMove(pointerEvent({ x: 60, y: 30, button: 2 }));

        expect(drag.onPointerUp(pointerEvent({ x: 60, y: 30, button: 2 }))).toEqual({
            start: null,
            box: null
        });
    });
});
