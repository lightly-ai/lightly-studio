import { afterEach, describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { tick } from 'svelte';
import ZoomableContainerTestWrapper from './ZoomableContainerTestWrapper.svelte';

class MockResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
}

describe('ZoomableContainer', () => {
    afterEach(() => {
        vi.unstubAllGlobals();
    });

    it('keeps focused viewBox stable when boundingBox changes for the same autoFocusKey', async () => {
        vi.stubGlobal('ResizeObserver', MockResizeObserver);

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
});
