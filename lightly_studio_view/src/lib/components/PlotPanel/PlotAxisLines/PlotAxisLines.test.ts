import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import PlotAxisLines from './PlotAxisLines.svelte';

// Puts the origin at pixel (originX, originY) in a 400 × 300 plot.
const createProxy = (originX: number, originY: number) => ({
    location: (x: number, y: number) => ({ x: x + originX, y: -y + originY }),
    width: 400,
    height: 300
});

describe('PlotAxisLines', () => {
    it('draws a line through the origin on each axis', () => {
        render(PlotAxisLines, { proxy: createProxy(120, 80) });

        expect(screen.getByTestId('plot-axis-line-x')).toHaveAttribute('x1', '120');
        expect(screen.getByTestId('plot-axis-line-y')).toHaveAttribute('y1', '80');
    });

    // Each case puts the origin just outside one side of the plot.
    it.each([
        [-1, 80, 'x'],
        [401, 80, 'x'],
        [120, -1, 'y'],
        [120, 301, 'y']
    ])('origin (%i, %i) hides only the %s line', (originX, originY, hidden) => {
        render(PlotAxisLines, { proxy: createProxy(originX, originY) });

        expect(screen.queryByTestId(`plot-axis-line-${hidden}`)).not.toBeInTheDocument();
        expect(screen.getAllByTestId(/^plot-axis-line-/)).toHaveLength(1);
    });
});
