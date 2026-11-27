import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import TimelineBuffer from './TimelineBuffer.svelte';

const defaultProps = {
    tickCount: 10,
    bufferedRanges: [] as { startIndex: number; endIndex: number }[]
};

describe('TimelineBuffer', () => {
    it('renders one continuous buffered range', () => {
        render(TimelineBuffer, {
            props: { ...defaultProps, bufferedRanges: [{ startIndex: 1, endIndex: 4 }] }
        });

        expect(document.querySelectorAll('[data-testid="timeline-buffered-range"]')).toHaveLength(
            1
        );
        expect(document.querySelector('[data-testid="timeline-buffered-range"]')).toHaveStyle({
            left: '10%',
            width: '40%'
        });
    });

    it('keeps separate ranges when buffered ranges are separated', () => {
        render(TimelineBuffer, {
            props: {
                ...defaultProps,
                bufferedRanges: [
                    { startIndex: 2, endIndex: 2 },
                    { startIndex: 4, endIndex: 4 }
                ]
            }
        });

        expect(document.querySelectorAll('[data-testid="timeline-buffered-range"]')).toHaveLength(
            2
        );
    });
});
