import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import PlotMarkers from './PlotMarkers.svelte';

// Maps data (x, y) to pixels (10x, 10y) in a 100 x 100 plot.
const proxy = {
    location: (x: number, y: number) => ({ x: x * 10, y: y * 10 }),
    width: 100,
    height: 100
};

describe('PlotMarkers', () => {
    it('shows the markers inside the plot at their pixel positions', () => {
        render(PlotMarkers, {
            props: {
                markers: [
                    { label: 'young sad', x: 2, y: 3 },
                    { label: 'old happy', x: 20, y: 3 }
                ],
                proxy
            }
        });

        const label = screen.getByText('young sad');
        expect(label.parentElement).toHaveStyle({ left: '20px', top: '30px' });
        expect(screen.queryByText('old happy')).not.toBeInTheDocument();
    });
});
