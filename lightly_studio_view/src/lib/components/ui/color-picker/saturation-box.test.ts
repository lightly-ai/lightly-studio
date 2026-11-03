import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import SaturationBox from './saturation-box.svelte';

const onPick = vi.fn();
const defaultProps = { hsl: { h: 0, s: 50, l: 50 }, onPick };

function getBox(): HTMLElement {
    const box = screen.getByRole('slider', { name: 'Saturation and lightness' });
    vi.spyOn(box, 'getBoundingClientRect').mockReturnValue({
        left: 0,
        top: 0,
        width: 100,
        height: 100
    } as DOMRect);
    return box;
}

describe('SaturationBox', () => {
    beforeAll(() => {
        // jsdom has no pointer capture and no PointerEvent, so pointer coordinates would be lost.
        HTMLElement.prototype.setPointerCapture = vi.fn();
        window.PointerEvent ??= class extends MouseEvent {
            pointerId: number;
            constructor(type: string, init: PointerEventInit = {}) {
                super(type, init);
                this.pointerId = init.pointerId ?? 0;
            }
        } as typeof PointerEvent;
    });

    beforeEach(() => {
        onPick.mockClear();
        render(SaturationBox, { props: defaultProps });
    });

    it('describes the current value', () => {
        const box = getBox();
        expect(box).toHaveAttribute('aria-valuetext', 'Saturation 50%, lightness 50%');
        expect(box).toHaveAttribute('tabindex', '0');
    });

    it('picks on pointer down and follows the drag until pointer up', async () => {
        const box = getBox();
        await fireEvent.pointerDown(box, { clientX: 100, clientY: 25, pointerId: 1 });
        expect(onPick).toHaveBeenLastCalledWith(100, 75);
        await fireEvent.pointerMove(box, { clientX: 50, clientY: 50, pointerId: 1 });
        expect(onPick).toHaveBeenLastCalledWith(50, 50);
        await fireEvent.pointerUp(box, { pointerId: 1 });
        await fireEvent.pointerMove(box, { clientX: 0, clientY: 0, pointerId: 1 });
        expect(onPick).toHaveBeenCalledTimes(2);
    });

    it('stops following the drag on pointer cancel', async () => {
        const box = getBox();
        await fireEvent.pointerDown(box, { clientX: 10, clientY: 10, pointerId: 1 });
        await fireEvent.pointerCancel(box, { pointerId: 1 });
        await fireEvent.pointerMove(box, { clientX: 0, clientY: 0, pointerId: 1 });
        expect(onPick).toHaveBeenCalledTimes(1);
    });

    it('clamps positions outside the box', async () => {
        const box = getBox();
        await fireEvent.pointerDown(box, { clientX: 150, clientY: -20, pointerId: 1 });
        expect(onPick).toHaveBeenLastCalledWith(100, 100);
    });

    it('moves with the arrow keys', async () => {
        const box = getBox();
        await fireEvent.keyDown(box, { key: 'ArrowRight' });
        expect(onPick).toHaveBeenLastCalledWith(51, 50);
        await fireEvent.keyDown(box, { key: 'ArrowDown' });
        expect(onPick).toHaveBeenLastCalledWith(50, 49);
        await fireEvent.keyDown(box, { key: 'ArrowUp', shiftKey: true });
        expect(onPick).toHaveBeenLastCalledWith(50, 60);
    });
});
