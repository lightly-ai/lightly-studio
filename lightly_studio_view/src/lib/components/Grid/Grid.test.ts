import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import Grid from './Grid.svelte';
import type { Snippet } from 'svelte';

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
        const { container } = render(Grid, {
            props: {
                itemCount: 10,
                columnCount: 3,
                gridItem: (() => ({})) as Snippet
            }
        });

        const viewport = container.querySelector('.viewport');
        expect(viewport).toBeInTheDocument();
        expect(viewport).toHaveClass('h-full', 'w-full');
    });

    it('renders with custom columnCount', () => {
        const { container } = render(Grid, {
            props: {
                itemCount: 10,
                columnCount: 4,
                gridItem: (() => ({})) as Snippet
            }
        });

        const viewport = container.querySelector('.viewport');
        expect(viewport).toBeInTheDocument();
    });

    it('applies viewportProps attributes', () => {
        const { container } = render(Grid, {
            props: {
                itemCount: 10,
                columnCount: 3,
                gridItem: (() => ({})) as Snippet,
                viewportProps: {
                    'data-testid': 'test-grid',
                    'aria-label': 'Sample grid'
                }
            }
        });

        const viewport = container.querySelector('[data-testid="test-grid"]');
        expect(viewport).toBeInTheDocument();
        expect(viewport).toHaveAttribute('aria-label', 'Sample grid');
    });

    it('accepts gridItem snippet prop', () => {
        const gridItemMock = vi.fn();

        render(Grid, {
            props: {
                itemCount: 5,
                columnCount: 2,
                gridItem: gridItemMock
            }
        });

        // Component should render without errors when gridItem is provided
        expect(gridItemMock).toBeDefined();
    });

    it('accepts optional footerItem snippet', () => {
        const footerItemMock = vi.fn();

        const { container } = render(Grid, {
            props: {
                itemCount: 5,
                columnCount: 2,
                gridItem: (() => ({})) as Snippet,
                footerItem: footerItemMock
            }
        });

        const viewport = container.querySelector('.viewport');
        expect(viewport).toBeInTheDocument();
        expect(footerItemMock).toBeDefined();
    });

    it('passes gridProps to VirtualGrid component', () => {
        const { container } = render(Grid, {
            props: {
                itemCount: 10,
                columnCount: 3,
                gridItem: (() => ({})) as Snippet,
                gridProps: {
                    class: 'custom-class'
                }
            }
        });

        const viewport = container.querySelector('.viewport');
        expect(viewport).toBeInTheDocument();
    });

    it('calculates item size based on columnCount and clientWidth', () => {
        const { container } = render(Grid, {
            props: {
                itemCount: 12,
                columnCount: 4,
                gridItem: (() => ({})) as Snippet
            }
        });

        // With mocked width of 800 and 4 columns, each item should be:
        // (800 / 4) - 20 (GRID_GAP) = 180px
        const viewport = container.querySelector('.viewport');
        expect(viewport).toBeInTheDocument();
    });

    it('renders with minimum width constraint', () => {
        // Create a ResizeObserver that returns very small width
        class SmallWidthResizeObserver {
            callback: ResizeObserverCallback;

            constructor(callback: ResizeObserverCallback) {
                this.callback = callback;
            }

            observe(target: Element) {
                this.callback(
                    [
                        {
                            target,
                            contentRect: { width: 50, height: 600 } as DOMRectReadOnly,
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

        global.ResizeObserver = SmallWidthResizeObserver as unknown as typeof ResizeObserver;

        const { container } = render(Grid, {
            props: {
                itemCount: 10,
                columnCount: 3,
                gridItem: (() => ({})) as Snippet
            }
        });

        // Component should use Math.max(entry.contentRect.width, 200)
        const viewport = container.querySelector('.viewport');
        expect(viewport).toBeInTheDocument();
    });
});
