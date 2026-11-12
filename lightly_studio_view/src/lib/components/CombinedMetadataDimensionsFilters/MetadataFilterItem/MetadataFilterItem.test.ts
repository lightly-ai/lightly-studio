import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import '@testing-library/jest-dom';
import MetadataFilterItem from './MetadataFilterItem.svelte';

describe('MetadataFilterItem', () => {
    // Regression guard: this exact float range made bits-ui's slider re-snap its value forever,
    // throwing effect_update_depth_exceeded on mount and freezing the image grid. Rendering the
    // component with a full-precision float range must not blow the effect-update depth limit.
    const solarAngle = { min: -75.89126551973673, max: 87.50941362154188 };

    it('mounts a full-precision float range without an effect-update loop', () => {
        const onValueCommit = vi.fn();

        expect(() =>
            render(MetadataFilterItem, {
                props: {
                    metadataKey: 'solar_angle',
                    bound: solarAngle,
                    value: { ...solarAngle },
                    isInteger: false,
                    onValueCommit
                }
            })
        ).not.toThrow();

        expect(screen.getByText('solar angle')).toBeInTheDocument();

        // Should not commit a filter just from mounting.
        expect(onValueCommit).not.toHaveBeenCalled();
    });

    const ranges = [
        {
            bound: { min: 0, max: 1 },
            value: { min: 0.123456789, max: 0.876543219 },
            isInteger: false
        },
        {
            bound: { min: 0, max: 28_000_000 },
            value: { min: 12345, max: 27_000_001 },
            isInteger: true
        }
    ];
    it.each(ranges.flatMap((props) => [0, 1].map((thumb) => ({ ...props, thumb }))))(
        'preserves the opposite endpoint when moving thumb $thumb: $isInteger',
        async ({ thumb, ...props }) => {
            const onValueCommit = vi.fn();
            render(MetadataFilterItem, { ...props, metadataKey: 'score', onValueCommit });
            const slider = screen.getAllByRole('slider')[thumb];
            const key = thumb === 0 ? 'ArrowRight' : 'ArrowLeft';
            await fireEvent.keyDown(slider, { key });
            await fireEvent.keyUp(slider, { key });
            expect(onValueCommit).toHaveBeenLastCalledWith('score', [
                thumb === 0 ? expect.any(Number) : props.value.min,
                thumb === 1 ? expect.any(Number) : props.value.max
            ]);
        }
    );
});
