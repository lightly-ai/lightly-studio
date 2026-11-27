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

    it('retries the restore when the height changes after a clamped scroll', async () => {
        const scroll = mockClampedScroll({ scrollHeight: 1000 });
        const { resize } = trackResizeObservers();
        render(GridTestWrapper, { props: { initialScrollPosition: 420 } });

        // 600px height allows a maximum scrollTop of 400.
        await waitFor(() => expect(scroll.top()).toBe(400));

        await act(() => resize(500));

        await waitFor(() => expect(scroll.top()).toBe(420));
    });

    it('stops the restore when the user scrolls', async () => {
        const scroll = mockClampedScroll({ scrollHeight: 1000 });
        const { resize } = trackResizeObservers();
        const { container } = render(GridTestWrapper, { props: { initialScrollPosition: 420 } });
        await waitFor(() => expect(scroll.top()).toBe(400));

        container.querySelector('.viewport')?.dispatchEvent(new Event('wheel'));
        await act(() => resize(500));

        const restoreCalls = vi
            .mocked(Element.prototype.scrollTo)
            .mock.calls.filter(([options]) => (options as ScrollToOptions).top === 420);
        expect(restoreCalls).toHaveLength(1);
        expect(scroll.top()).toBe(400);
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

function mockClampedScroll({ scrollHeight }: { scrollHeight: number }) {
    let scrollTop = 0;
    vi.spyOn(Element.prototype, 'scrollTop', 'get').mockImplementation(() => scrollTop);
    Element.prototype.scrollTo = vi.fn(function (
        this: Element,
        options?: ScrollToOptions | number
    ) {
        const top = typeof options === 'number' ? 0 : (options?.top ?? 0);
        scrollTop = Math.min(top, scrollHeight - this.clientHeight);
    }) as typeof Element.prototype.scrollTo;
    return { top: () => scrollTop };
}

function trackResizeObservers() {
    const observed: Array<[MockResizeObserver, Element]> = [];
    const observe = MockResizeObserver.prototype.observe;
    vi.spyOn(MockResizeObserver.prototype, 'observe').mockImplementation(function (
        this: MockResizeObserver,
        target: Element
    ) {
        observed.push([this, target]);
        observe.call(this, target);
    });

    const resize = (clientHeight: number) => {
        vi.spyOn(HTMLElement.prototype, 'clientHeight', 'get').mockReturnValue(clientHeight);
        for (const [observer, target] of observed) {
            observe.call(observer, target);
        }
    };
    return { resize };
}
