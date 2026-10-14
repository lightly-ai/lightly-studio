import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import TimelineBufferedRange from './TimelineBufferedRange.svelte';

const defaultProps = { startIndex: 0, endIndex: 0, tickCount: 10 };

describe('TimelineBufferedRange', () => {
    it('computes left and width from tick indices', () => {
        render(TimelineBufferedRange, {
            props: { ...defaultProps, startIndex: 1, endIndex: 4, tickCount: 10 }
        });

        const el = document.querySelector('[data-testid="timeline-buffered-range"]');
        expect(el).toHaveStyle({ left: '10%', width: '40%' });
    });

    it('falls back to 0% when tickCount is 0', () => {
        render(TimelineBufferedRange, {
            props: { ...defaultProps, startIndex: 2, endIndex: 5, tickCount: 0 }
        });

        const el = document.querySelector('[data-testid="timeline-buffered-range"]');
        expect(el).toHaveStyle({ left: '0%', width: '0%' });
    });
});
