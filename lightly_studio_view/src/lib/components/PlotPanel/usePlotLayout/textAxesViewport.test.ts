import { describe, expect, it } from 'vitest';
import { getDefaultViewport } from './textAxesViewport';

const PLOT_AXES = { x: [1, 0], y: [0, 1] };

describe('getDefaultViewport', () => {
    it('fits PaCMAP to the data', () => {
        expect(getDefaultViewport({ plotAxes: null, width: 800, height: 400 })).toBeNull();
    });

    it('shows -0.2 to 0.2 on the shorter side of the plot, centered on the origin', () => {
        expect(getDefaultViewport({ plotAxes: PLOT_AXES, width: 400, height: 400 })).toEqual({
            x: 0,
            y: 0,
            scale: 5
        });
        expect(getDefaultViewport({ plotAxes: PLOT_AXES, width: 800, height: 400 })?.scale).toBe(
            2.5
        );
        expect(getDefaultViewport({ plotAxes: PLOT_AXES, width: 400, height: 800 })?.scale).toBe(
            2.5
        );
    });
});
