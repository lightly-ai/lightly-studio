import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import PlotPointSizeControl from './PlotPointSizeControl.svelte';
import { getNextPointSize } from './pointSize';

describe('getNextPointSize', () => {
    it('steps through the sizes around Auto and clamps at the ends', () => {
        expect(getNextPointSize(null, 1)).toBe(3);
        expect(getNextPointSize(null, -1)).toBe(2);
        expect(getNextPointSize(6, 1)).toBe(6);
        expect(getNextPointSize(1, -1)).toBe(1);
    });
});

describe('PlotPointSizeControl', () => {
    it('starts at Auto and grows the points on plus', async () => {
        render(PlotPointSizeControl, { pointSize: null });

        expect(screen.getByTestId('plot-point-size-value')).toHaveTextContent('Auto');
        await fireEvent.click(screen.getByTestId('plot-point-size-increase'));
        expect(screen.getByTestId('plot-point-size-value')).toHaveTextContent('3');
    });
});
