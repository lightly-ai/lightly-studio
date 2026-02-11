import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render } from '@testing-library/svelte';
import { tick } from 'svelte';
import ZoomableContainerTestWrapper from './ZoomableContainerTestWrapper.svelte';

class MockResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
}

// jsdom doesn't implement SVGAnimatedRect, so d3-zoom crashes when it
// accesses SVGSVGElement.viewBox.baseVal during zoom transitions.
// Applied at module level — the jsdom environment is torn down per file.
Object.defineProperty(SVGSVGElement.prototype, 'viewBox', {
    get() {
        const attr = this.getAttribute('viewBox');
        if (attr) {
            const [x, y, width, height] = attr.split(' ').map(Number);
            return { baseVal: { x, y, width, height } };
        }
        return { baseVal: { x: 0, y: 0, width: 0, height: 0 } };
    },
    configurable: true
});

describe('ZoomableContainer', () => {
    beforeEach(() => {
        // Fake timers prevent d3-transition's requestAnimationFrame callbacks
        // from firing asynchronously after test teardown.
        vi.useFakeTimers();
        vi.stubGlobal('ResizeObserver', MockResizeObserver);
    });

    afterEach(() => {
        vi.useRealTimers();
        vi.unstubAllGlobals();
    });

    it('keeps focused viewBox stable when boundingBox changes for the same autoFocusKey', async () => {
        const { container, rerender } = render(ZoomableContainerTestWrapper, {
            props: {
                boundingBox: { x: 100, y: 120, width: 80, height: 60 },
                autoFocusEnabled: true,
                autoFocusKey: 'annotation-1'
            }
        });

        await tick();

        const svg = container.querySelector('svg.z-10');
        expect(svg).toBeTruthy();
        expect(svg!.getAttribute('viewBox')).toBe('90 110 100 80');

        await rerender({
            boundingBox: { x: 640, y: 510, width: 50, height: 40 },
            autoFocusEnabled: true,
            autoFocusKey: 'annotation-1'
        });

        await tick();

        expect(svg!.getAttribute('viewBox')).toBe('90 110 100 80');
    });

    it('updates viewBox when autoFocusKey changes', async () => {
        const { container, rerender } = render(ZoomableContainerTestWrapper, {
            props: {
                boundingBox: { x: 100, y: 120, width: 80, height: 60 },
                autoFocusEnabled: true,
                autoFocusKey: 'ann-1'
            }
        });

        await tick();

        const svg = container.querySelector('svg.z-10');
        expect(svg).toBeTruthy();
        expect(svg!.getAttribute('viewBox')).toBe('90 110 100 80');

        await rerender({
            boundingBox: { x: 200, y: 300, width: 120, height: 100 },
            autoFocusEnabled: true,
            autoFocusKey: 'ann-2'
        });

        await tick();

        expect(svg!.getAttribute('viewBox')).toBe('190 290 140 120');
    });

    it('reset button recenters to latest bounding box after silent update', async () => {
        const { container, rerender } = render(ZoomableContainerTestWrapper, {
            props: {
                boundingBox: { x: 100, y: 120, width: 80, height: 60 },
                autoFocusEnabled: true,
                autoFocusKey: 'ann-1'
            }
        });

        await tick();

        const svg = container.querySelector('svg.z-10');
        expect(svg).toBeTruthy();
        expect(svg!.getAttribute('viewBox')).toBe('90 110 100 80');

        // Rerender with same key but different bbox — viewBox should stay stable
        await rerender({
            boundingBox: { x: 200, y: 300, width: 120, height: 100 },
            autoFocusEnabled: true,
            autoFocusKey: 'ann-1'
        });

        await tick();

        expect(svg!.getAttribute('viewBox')).toBe('90 110 100 80');

        // Click reset — should recenter to the latest (silently updated) bbox
        const resetButton = container.querySelector('[data-testid="zoom-reset-button"]');
        expect(resetButton).toBeTruthy();
        await fireEvent.click(resetButton!);

        await tick();

        expect(svg!.getAttribute('viewBox')).toBe('190 290 140 120');
    });

    it('preserves focus when boundingBox becomes undefined but autoFocusKey is set', async () => {
        const { container, rerender } = render(ZoomableContainerTestWrapper, {
            props: {
                boundingBox: { x: 100, y: 120, width: 80, height: 60 },
                autoFocusEnabled: true,
                autoFocusKey: 'ann-1'
            }
        });

        await tick();

        const svg = container.querySelector('svg.z-10');
        expect(svg).toBeTruthy();
        expect(svg!.getAttribute('viewBox')).toBe('90 110 100 80');

        // Rerender with undefined boundingBox but same key — simulates data refetch
        await rerender({
            boundingBox: undefined,
            autoFocusEnabled: true,
            autoFocusKey: 'ann-1'
        });

        await tick();

        // viewBox should remain focused on the original bbox
        expect(svg!.getAttribute('viewBox')).toBe('90 110 100 80');
    });
});
