import { describe, expect, it } from 'vitest';
import { useTimelineViewport } from './useTimelineViewport.svelte';

describe('useTimelineViewport', () => {
    it('keeps the current frame in place when zooming with the buttons', () => {
        const viewport = useTimelineViewport(
            () => 654,
            () => 160
        );
        const position = 160.5 / 654;
        viewport.zoomBy(1.5);
        expect((position - viewport.offset) * viewport.zoom).toBeCloseTo(position);
        viewport.zoomBy(1 / 1.5);
        expect(viewport.offset).toBeCloseTo(0);
    });

    it('starts unzoomed and limits zoom so at least 10 ticks stay visible', () => {
        const viewport = useTimelineViewport(() => 100);
        expect(viewport.zoom).toBe(1);
        expect(viewport.canZoomOut).toBe(false);

        viewport.zoomBy(1000);
        expect(viewport.zoom).toBe(10);
        expect(viewport.canZoomIn).toBe(false);

        viewport.zoomBy(0.0001);
        expect(viewport.zoom).toBe(1);
        expect(viewport.offset).toBe(0);
    });

    it('does not zoom a sequence with fewer than 10 ticks', () => {
        const viewport = useTimelineViewport(() => 5);
        viewport.zoomBy(2);
        expect(viewport.zoom).toBe(1);
    });

    it('keeps the anchored point fixed while zooming', () => {
        const viewport = useTimelineViewport(() => 1000);
        viewport.zoomBy(4, 0.25);
        // The point at 25% of the full timeline stays at 25% of the window.
        expect(viewport.offset + 0.25 / viewport.zoom).toBeCloseTo(0.25);

        const rightEdge = viewport.offset + 1 / viewport.zoom;
        viewport.zoomBy(2, 1);
        expect(viewport.offset + 1 / viewport.zoom).toBeCloseTo(rightEdge);
    });

    it('clamps panning to the timeline', () => {
        const viewport = useTimelineViewport(() => 1000);
        viewport.zoomBy(4);
        viewport.panBy(-1);
        expect(viewport.offset).toBe(0);
        viewport.panBy(5);
        expect(viewport.offset).toBeCloseTo(0.75);
    });

    it('reveals a hidden tick but leaves a visible one alone', () => {
        const viewport = useTimelineViewport(() => 1000);
        viewport.zoomBy(10, 0);
        viewport.reveal(50);
        expect(viewport.offset).toBe(0);

        viewport.reveal(900);
        expect(viewport.offset * 1000).toBeLessThanOrEqual(900);
        expect((viewport.offset + 1 / viewport.zoom) * 1000).toBeGreaterThan(900);
    });

    it('uses native scroll offsets for subsequent zooming and clamps them at both ends', () => {
        const viewport = useTimelineViewport(() => 1000);
        viewport.zoomBy(4, 0);
        viewport.setOffset(0.4);
        viewport.zoomBy(2, 0.5);
        expect(viewport.offset + 0.5 / viewport.zoom).toBeCloseTo(0.525);

        viewport.setOffset(1);
        expect(viewport.offset).toBeCloseTo(1 - 1 / viewport.zoom);
        viewport.setOffset(-1);
        expect(viewport.offset).toBe(0);
    });

    it('resets to the full timeline', () => {
        const viewport = useTimelineViewport(() => 1000);
        viewport.zoomBy(4, 0.5);
        viewport.reset();
        expect(viewport.zoom).toBe(1);
        expect(viewport.offset).toBe(0);
    });

    it('shows an explicit window, keeping it within the timeline and zoom limits', () => {
        const viewport = useTimelineViewport(() => 100);
        viewport.setWindow(0.25, 0.75);
        expect(viewport.zoom).toBeCloseTo(2);
        expect(viewport.offset).toBeCloseTo(0.25);

        viewport.setWindow(0.5, 0.5);
        expect(viewport.zoom).toBe(10);

        viewport.setWindow(0.9, 1.5);
        expect(viewport.offset).toBeLessThanOrEqual(1 - 1 / viewport.zoom);
    });
});
