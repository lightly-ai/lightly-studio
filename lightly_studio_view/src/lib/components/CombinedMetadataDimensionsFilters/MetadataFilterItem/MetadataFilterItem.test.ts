import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import '@testing-library/jest-dom';
import MetadataFilterItem from './MetadataFilterItem.svelte';

describe('MetadataFilterItem', () => {
    // Regression guard: this exact float range made bits-ui's slider re-snap its value forever,
    // throwing effect_update_depth_exceeded on mount and freezing the image grid. Rendering the
    // component with a full-precision float range must not blow the effect-update depth limit.
    const solarAngle = { min: -75.89126551973673, max: 87.50941362154188 };

    it('mounts a full-precision float range without an effect-update loop', () => {
        expect(() =>
            render(MetadataFilterItem, {
                props: {
                    metadataKey: 'solar_angle',
                    bound: solarAngle,
                    value: { ...solarAngle },
                    onValueCommit: vi.fn()
                }
            })
        ).not.toThrow();

        expect(screen.getByText('solar angle')).toBeInTheDocument();
    });

    it('does not commit a filter just from mounting', () => {
        const onValueCommit = vi.fn();

        render(MetadataFilterItem, {
            props: {
                metadataKey: 'solar_angle',
                bound: solarAngle,
                value: { ...solarAngle },
                onValueCommit
            }
        });

        expect(onValueCommit).not.toHaveBeenCalled();
    });
});
