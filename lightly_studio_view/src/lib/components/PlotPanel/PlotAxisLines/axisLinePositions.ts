import type { OverlayProxy } from 'embedding-atlas/svelte';

/**
 * Returns the pixel position of the line x = 0 (a vertical line) and of the line y = 0 (a
 * horizontal line). A line outside the visible plot is null.
 */
export const getAxisLinePositions = (
    proxy: OverlayProxy
): { x: number | null; y: number | null } => {
    const origin = proxy.location(0, 0);
    return {
        x: isInRange(origin.x, proxy.width) ? origin.x : null,
        y: isInRange(origin.y, proxy.height) ? origin.y : null
    };
};

const isInRange = (value: number, max: number) => value >= 0 && value <= max;
