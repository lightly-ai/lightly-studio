import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import GridTestWrapper from './GridTestWrapper.test.svelte';

class MockResizeObserver {
    callback: ResizeObserverCallback;

    constructor(callback: ResizeObserverCallback) {
        this.callback = callback;
    }

    observe(target: Element) {
        // Simulate initial observation with a width
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
        global.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;

        // Mock scrollTo for the virtual grid
        Element.prototype.scrollTo = vi.fn();
    });

    it('renders viewport container', () => {
        const { container } = render(GridTestWrapper);

        const viewport = container.querySelector('.viewport');
        expect(viewport).toBeInTheDocument();
        expect(viewport).toHaveClass('h-full', 'w-full');
    });

    it('renders grid items with correct data attributes', () => {
        const { container } = render(GridTestWrapper);

        const gridItem = container.querySelector('[data-testid="grid-item-0"]');
        expect(gridItem).toBeInTheDocument();
    });

    it('calls gridItem with correct parameters', () => {
        const { container } = render(GridTestWrapper);

        const gridItem = container.querySelector('[data-testid="grid-item-0"]');
        expect(gridItem).toBeInTheDocument();

        // Check that the gridItem receives style attribute (from VirtualGrid)
        expect(gridItem).toHaveAttribute('style');

        // The style should contain positioning from VirtualGrid
        const style = gridItem?.getAttribute('style');
        expect(style).toBeTruthy();
    });

    it('renders multiple grid items', () => {
        const { container } = render(GridTestWrapper);

        const firstItem = container.querySelector('[data-testid="grid-item-0"]');
        const secondItem = container.querySelector('[data-testid="grid-item-1"]');
        expect(firstItem).toBeInTheDocument();
        expect(secondItem).toBeInTheDocument();
    });

    it('renders correct number of items based on itemCount', () => {
        const { container } = render(GridTestWrapper);

        // GridTestWrapper has itemCount={100}
        // VirtualGrid only renders visible items initially, not all 100 at once
        const items = container.querySelectorAll('[data-testid^="grid-item-"]');
        expect(items.length).toBeGreaterThan(0);
        expect(items.length).toBeLessThan(100);
    });

    it('can scroll to the end of the list', async () => {
        const { container } = render(GridTestWrapper);

        const gridScroll = container.querySelector('.grid-scroll');

        if (gridScroll) {
            let item19 = null;
            let scrollPosition = 0;

            // Check that we do not have grid-item-19 initially
            expect(container.querySelector('[data-testid="grid-item-19"]')).not.toBeInTheDocument();

            // Scroll until we find grid-item-19
            while (!item19 && scrollPosition < 3000) {
                scrollPosition += 500;

                Object.defineProperty(gridScroll, 'scrollTop', {
                    writable: true,
                    configurable: true,
                    value: scrollPosition
                });

                gridScroll.dispatchEvent(new Event('scroll'));
                await new Promise((resolve) => setTimeout(resolve, 100));

                item19 = container.querySelector('[data-testid="grid-item-19"]');
            }

            // Should be able to scroll and see grid-item-19
            expect(item19).toBeInTheDocument();
        }
    });
});
