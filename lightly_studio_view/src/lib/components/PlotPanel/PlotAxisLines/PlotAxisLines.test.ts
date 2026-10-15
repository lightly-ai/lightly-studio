import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import PlotAxisLines from './PlotAxisLines.svelte';

const createProxy = (offsetX: number, offsetY: number) => ({
    location: (x: number, y: number) => ({ x: x + offsetX, y: -y + offsetY }),
    width: 400,
    height: 300
});

describe('PlotAxisLines', () => {
    it('draws a line through the origin on each axis', () => {
        render(PlotAxisLines, { proxy: createProxy(120, 80) });

        expect(screen.getByTestId('plot-axis-line-x')).toHaveAttribute('x1', '120');
        expect(screen.getByTestId('plot-axis-line-y')).toHaveAttribute('y1', '80');
    });

    it('hides a line whose origin is outside the plot', () => {
        render(PlotAxisLines, { proxy: createProxy(-50, 80) });

        expect(screen.queryByTestId('plot-axis-line-x')).not.toBeInTheDocument();
        expect(screen.getByTestId('plot-axis-line-y')).toBeInTheDocument();
    });
});
