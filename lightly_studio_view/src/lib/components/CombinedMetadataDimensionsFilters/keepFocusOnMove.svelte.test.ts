import { render, screen } from '@testing-library/svelte';
import { tick } from 'svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import KeepFocusOnMoveHarness from './KeepFocusOnMoveHarness.test.svelte';

// jsdom has no layout, so scroll positions are stored on the element.
const storeScrollTop = (element: HTMLElement, initial: number) => {
    let value = initial;
    Object.defineProperty(element, 'scrollTop', {
        configurable: true,
        get: () => value,
        set: (next: number) => {
            value = next;
        }
    });
};

const rowTops = (...tops: number[]) => {
    const rect = vi.spyOn(Element.prototype, 'getBoundingClientRect');
    for (const top of tops) rect.mockReturnValueOnce({ top } as DOMRect);
    return rect;
};

describe('keepFocusOnMove', () => {
    afterEach(() => vi.restoreAllMocks());

    it('keeps focus on an input whose row moves to the top', async () => {
        const { rerender } = render(KeepFocusOnMoveHarness, {
            order: ['a', 'b'],
            blurOnChange: true
        });
        const button = screen.getByRole('button', { name: 'b' });
        button.focus();
        const focus = vi.spyOn(button, 'focus');

        await rerender({ order: ['b', 'a'] });
        await tick();

        expect(focus).toHaveBeenCalledWith({ preventScroll: true });
        expect(document.activeElement).toBe(button);
    });

    it('scrolls the panel so the moved row stays at the same screen position', async () => {
        const { rerender } = render(KeepFocusOnMoveHarness, { order: ['a', 'b'] });
        const scroller = screen.getByTestId('scroller');
        storeScrollTop(scroller, 400);
        screen.getByRole('button', { name: 'b' }).focus();
        rowTops(300, 50);

        await rerender({ order: ['b', 'a'] });
        await tick();

        expect(scroller.scrollTop).toBe(150);
    });

    it('restores the scroll position inside the moved row', async () => {
        const { rerender } = render(KeepFocusOnMoveHarness, {
            order: ['a', 'b'],
            resetScrollOnChange: true
        });
        const inner = screen.getByTestId('inner-b');
        storeScrollTop(inner, 80);
        screen.getByRole('button', { name: 'b' }).focus();

        await rerender({ order: ['b', 'a'] });
        await tick();

        expect(inner.scrollTop).toBe(80);
    });

    it('does nothing when focus is outside the container', async () => {
        const { rerender } = render(KeepFocusOnMoveHarness, { order: ['a', 'b'] });
        const scroller = screen.getByTestId('scroller');
        storeScrollTop(scroller, 400);
        screen.getByRole('button', { name: 'outside' }).focus();
        const rect = rowTops(300, 50);

        await rerender({ order: ['b', 'a'] });
        await tick();

        expect(document.activeElement).toBe(screen.getByRole('button', { name: 'outside' }));
        expect(rect).not.toHaveBeenCalled();
        expect(scroller.scrollTop).toBe(400);
    });

    it('does nothing when the order is unchanged', async () => {
        const { rerender } = render(KeepFocusOnMoveHarness, { order: ['a', 'b'] });
        screen.getByRole('button', { name: 'b' }).focus();
        const rect = rowTops(300, 50);

        await rerender({ order: ['a', 'b'] });
        await tick();

        expect(rect).not.toHaveBeenCalled();
    });
});
