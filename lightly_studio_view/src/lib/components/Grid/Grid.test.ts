import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, waitFor } from '@testing-library/svelte';
import GridTestWrapper from './GridTestWrapper.test.svelte';

class MockResizeObserver {
    callback: ResizeObserverCallback;

    constructor(callback: ResizeObserverCallback) {
        this.callback = callback;
    }

    observe(target: Element) {
        this.callback(
            [
                {
                    target,
                    contentRect: { width: 800, height: 600 } as DOMRectReadOnly,
                    borderBoxSize: [] as ReadonlyArray<ResizeObserverSize>,
                    contentBoxSize: [] as ReadonlyArray<ResizeObserverSize>,
                    devicePixelContentBoxSize: [] as ReadonlyArray<ResizeObserverSize>
                }
            ],
            this
        );
    }

    unobserve() {}
    disconnect() {}
}

describe('Grid', () => {
    beforeEach(() => {
        vi.restoreAllMocks();
        global.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;
        Element.prototype.scrollTo = vi.fn();
        vi.spyOn(HTMLElement.prototype, 'clientHeight', 'get').mockReturnValue(600);

        vi.spyOn(window, 'requestAnimationFrame').mockImplementation((callback) => {
            callback(0);
            return 0;
        });
    });

    it('renders viewport container and virtualized items', () => {
        const { container } = render(GridTestWrapper);

        const viewport = container.querySelector('.viewport');
        expect(viewport).toBeInTheDocument();

        const firstItem = container.querySelector('[data-testid="grid-item-0"]');
        expect(firstItem).toBeInTheDocument();
    });

    it('waits for layout before mounting only visible and overscan items', async () => {
        const observers: MockResizeObserver[] = [];
        const observe = vi
            .spyOn(MockResizeObserver.prototype, 'observe')
            .mockImplementation(function (this: MockResizeObserver) {
                observers.push(this);
            });
        const { container } = render(GridTestWrapper, {
            props: { itemCount: 100, columnCount: 6, overScan: 2 }
        });
        expect(container.querySelectorAll('[data-testid^="grid-item-"]')).toHaveLength(0);

        await act(() => {
            observe.mockRestore();
            for (const observer of observers) {
                observer.observe(container);
            }
        });

        await waitFor(() => {
            // 804px width gives 134px cells: five visible rows plus two overscan rows.
            expect(container.querySelectorAll('[data-testid^="grid-item-"]')).toHaveLength(42);
        });
    });

    it('renders the footer snippet', () => {
        const { container } = render(GridTestWrapper);

        const footer = container.querySelector('[data-testid="grid-footer"]');
        expect(footer).toBeInTheDocument();
    });

    it('forwards scroll events through onScroll', () => {
        const onScroll = vi.fn();
        const { container } = render(GridTestWrapper, { props: { onScroll } });

        const grid = container.querySelector('[data-testid="grid"]');
        expect(grid).toBeInTheDocument();

        if (!grid) {
            throw new Error('Expected grid element to be rendered');
        }

        Object.defineProperty(grid, 'scrollTop', {
            writable: true,
            configurable: true,
            value: 120
        });

        grid.dispatchEvent(new Event('scroll'));

        expect(onScroll).toHaveBeenCalledTimes(1);
    });

    it('restores initial scroll position', async () => {
        render(GridTestWrapper, { props: { initialScrollPosition: 420 } });

        await waitFor(() => {
            expect(Element.prototype.scrollTo).toHaveBeenCalledWith(
                expect.objectContaining({ top: 420 })
            );
        });
    });

    it('resets scroll when scrollResetKey changes', async () => {
        const { rerender } = render(GridTestWrapper, {
            props: { scrollResetKey: 'initial' }
        });

        await rerender({ scrollResetKey: 'changed' });

        await waitFor(() => {
            expect(Element.prototype.scrollTo).toHaveBeenCalledWith(
                expect.objectContaining({ top: 0 })
            );
        });
    });
});
