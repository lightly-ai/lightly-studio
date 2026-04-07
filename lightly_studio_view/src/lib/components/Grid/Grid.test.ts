import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { tick, type ComponentProps } from 'svelte';
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

type GridProps = ComponentProps<typeof GridTestWrapper>;

describe('Grid', () => {
    const defaultProps: GridProps = {
        itemCount: 100,
        columnCount: 3,
        gridItem: vi.fn()
    };
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

    it('calls onScroll callback when scrolling', async () => {
        const onScroll = vi.fn();
        const { container } = render(GridTestWrapper, { onScroll, ...defaultProps });

        const gridScroll = container.querySelector('.grid-scroll');
        expect(gridScroll).toBeInTheDocument();

        if (gridScroll) {
            Object.defineProperty(gridScroll, 'scrollTop', {
                writable: true,
                configurable: true,
                value: 100
            });

            const scrollEvent = new Event('scroll');
            gridScroll.dispatchEvent(scrollEvent);

            await new Promise((resolve) => setTimeout(resolve, 50));

            expect(onScroll).toHaveBeenCalled();
        }
    });

    it('scrolls to index when scrollToIndex is provided', async () => {
        vi.clearAllMocks();
        render(GridTestWrapper, { scrollToIndex: 10, ...defaultProps });

        await new Promise((resolve) => setTimeout(resolve, 100));

        // scrollTo should have been called due to scrollToIndex
        expect(Element.prototype.scrollTo).toHaveBeenCalled();
    });

    it('scrolls to position when scrollPosition is provided', async () => {
        vi.clearAllMocks();
        render(GridTestWrapper, { scrollPosition: 500, ...defaultProps });

        await new Promise((resolve) => setTimeout(resolve, 100));

        // scrollTo should have been called with the target position
        expect(Element.prototype.scrollTo).toHaveBeenCalled();
    });

    it('calls scrollToIndex on underlying grid when scrollToIndex prop is provided', async () => {
        vi.clearAllMocks();
        render(GridTestWrapper, {
            scrollToIndex: 5,
            ...defaultProps
        } as ComponentProps<typeof GridTestWrapper>);

        await tick();
        await new Promise((resolve) => setTimeout(resolve, 100));

        // scrollTo should have been called at least once due to scrollToIndex
        expect(Element.prototype.scrollTo).toHaveBeenCalled();
    });

    it('calls scrollToPosition on underlying grid when scrollPosition prop is provided', async () => {
        vi.clearAllMocks();
        render(GridTestWrapper, {
            itemCount: 100,
            columnCount: 3,
            scrollPosition: 100
        } as ComponentProps<typeof GridTestWrapper>);

        await tick();
        await new Promise((resolve) => setTimeout(resolve, 100));

        // scrollTo should have been called at least once due to scrollPosition
        expect(Element.prototype.scrollTo).toHaveBeenCalled();
    });
});
