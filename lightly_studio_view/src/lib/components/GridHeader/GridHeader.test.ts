import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import { tick } from 'svelte';
import { writable } from 'svelte/store';
import GridHeaderTest from './GridHeaderTest.test.svelte';
import '@testing-library/jest-dom';

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({
        updateSampleSize: vi.fn(),
        sampleSize: writable({ width: 4 })
    })
}));

interface MockResizeObserver {
    trigger: () => void;
}
const resizeObservers = (
    globalThis.ResizeObserver as unknown as { instances: MockResizeObserver[] }
).instances;

// Drive the bar's ResizeObserver: set widths, fire the observer, flush reactivity.
async function resizeTo(el: Element, scrollWidth: number, clientWidth: number): Promise<void> {
    Object.defineProperty(el, 'scrollWidth', { configurable: true, value: scrollWidth });
    Object.defineProperty(el, 'clientWidth', { configurable: true, value: clientWidth });
    resizeObservers.at(-1)?.trigger();
    await tick();
}

describe('GridHeader', () => {
    it('renders children snippet when provided', () => {
        const { container } = render(GridHeaderTest, {
            props: {
                testCase: 'children-only'
            }
        });

        expect(container.textContent).toContain('Test Title');
    });

    it('renders ImageSizeControl by default', () => {
        render(GridHeaderTest, {
            props: {
                testCase: 'children-only'
            }
        });

        const zoomOutButton = screen.getByLabelText('Zoom out');
        expect(zoomOutButton).toBeInTheDocument();
    });

    it('does not render ImageSizeControl when showImageSizeControl is false', () => {
        render(GridHeaderTest, {
            props: {
                testCase: 'no-image-size-control'
            }
        });

        const zoomOutButton = screen.queryByLabelText('Zoom out');
        expect(zoomOutButton).not.toBeInTheDocument();
    });

    it('renders auxControls snippet when provided', () => {
        const { container } = render(GridHeaderTest, {
            props: {
                testCase: 'with-aux-controls'
            }
        });

        expect(container.textContent).toContain('Aux Controls');
    });

    it('renders selectionControls snippet when provided', () => {
        const { container } = render(GridHeaderTest, {
            props: {
                testCase: 'with-selection-controls'
            }
        });

        expect(container.textContent).toContain('Selection Controls');
    });

    it('renders all elements together when provided', () => {
        const { container } = render(GridHeaderTest, {
            props: {
                testCase: 'all-elements'
            }
        });

        expect(container.textContent).toContain('Main Content');
        expect(container.textContent).toContain('Selection Controls');
        expect(container.textContent).toContain('Extra Controls');
        expect(screen.getByLabelText('Zoom out')).toBeInTheDocument();
    });

    it('lays out controls in a single non-wrapping flex row by default', () => {
        const { container } = render(GridHeaderTest, {
            props: {
                testCase: 'children-only'
            }
        });

        const wrapper = container.querySelector('.flex.flex-nowrap');
        expect(wrapper).toBeInTheDocument();
        expect(wrapper).not.toHaveClass('flex-wrap');
    });

    it('gives the children region flexible width', () => {
        const { container } = render(GridHeaderTest, {
            props: {
                testCase: 'children-only'
            }
        });

        const childrenContainer = container.querySelector('.flex-1');
        expect(childrenContainer).toBeInTheDocument();
    });

    it('compacts, then wraps, then re-expands as the row resizes', async () => {
        const { container } = render(GridHeaderTest, {
            props: {
                testCase: 'compact-probe'
            }
        });

        const bar = container.querySelector('.my-2')!;
        expect(screen.getByTestId('compact-state')).toHaveTextContent('full');
        expect(bar).not.toHaveClass('flex-wrap');

        // Row no longer fits on one line -> compact (records expanded width 600).
        await resizeTo(bar, 600, 400);
        expect(screen.getByTestId('compact-state')).toHaveTextContent('compact');
        expect(bar).not.toHaveClass('flex-wrap');

        // Even compacted it still overflows -> wrap onto a second row (records width 500).
        // flex-nowrap and flex-wrap are conflicting utilities, so only one may be applied.
        await resizeTo(bar, 500, 400);
        expect(bar).toHaveClass('flex-wrap');
        expect(bar).not.toHaveClass('flex-nowrap');

        // Wide enough for the compact layout again -> stop wrapping.
        await resizeTo(bar, 500, 520);
        expect(bar).not.toHaveClass('flex-wrap');
        expect(screen.getByTestId('compact-state')).toHaveTextContent('compact');

        // Wide enough for the full layout again -> re-expand.
        await resizeTo(bar, 500, 620);
        expect(screen.getByTestId('compact-state')).toHaveTextContent('full');
    });
});
