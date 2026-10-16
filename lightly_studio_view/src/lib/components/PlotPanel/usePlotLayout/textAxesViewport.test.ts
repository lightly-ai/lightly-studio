import { describe, expect, it } from 'vitest';
import { getDefaultViewport } from './textAxesViewport';

describe('getDefaultViewport', () => {
    it('fits PaCMAP to the data', () => {
        expect(getDefaultViewport({ hasTextAxes: false, width: 800, height: 400 })).toBeNull();
    });

    it('shows -0.2 to 0.2 on the shorter side of the plot, centered on the origin', () => {
        expect(getDefaultViewport({ hasTextAxes: true, width: 400, height: 400 })).toEqual({
            x: 0,
            y: 0,
            scale: 5
        });
        expect(getDefaultViewport({ hasTextAxes: true, width: 800, height: 400 })?.scale).toBe(2.5);
        expect(getDefaultViewport({ hasTextAxes: true, width: 400, height: 800 })?.scale).toBe(2.5);
    });
});
