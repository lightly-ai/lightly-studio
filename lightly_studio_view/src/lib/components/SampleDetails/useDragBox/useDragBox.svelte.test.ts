import { describe, expect, it, vi } from 'vitest';
import { useDragBox } from './useDragBox.svelte';

describe('useDragBox', () => {
    it('ignores buttons other than the primary one', () => {
        const rect = {
            getBoundingClientRect: () => ({ left: 0, top: 0, width: 100, height: 100 })
        };
        const drag = useDragBox(() => ({ interactionRect: rect as unknown as SVGRectElement }));
        const rightClick = {
            clientX: 10,
            clientY: 10,
            button: 2,
            currentTarget: { setPointerCapture: vi.fn(), releasePointerCapture: vi.fn() }
        } as unknown as PointerEvent & { currentTarget: SVGRectElement };

        drag.onPointerDown(rightClick);

        expect(drag.onPointerUp(rightClick)).toEqual({ start: null, box: null });
    });
});
