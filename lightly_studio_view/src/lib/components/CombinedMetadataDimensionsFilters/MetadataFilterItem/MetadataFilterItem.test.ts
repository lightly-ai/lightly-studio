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
                    onValueCommit
                }
            })
        ).not.toThrow();

        expect(screen.getByRole('heading', { name: 'solar_angle' })).toBeInTheDocument();

        // Should not commit a filter just from mounting.
        expect(onValueCommit).not.toHaveBeenCalled();
    });

    it('hides the slider while collapsed and toggles from the field name', async () => {
        const onToggleExpanded = vi.fn();
        render(MetadataFilterItem, {
            props: {
                metadataKey: 'score',
                bound: { min: 0, max: 1 },
                value: { min: 0, max: 1 },
                onValueCommit: vi.fn(),
                expanded: false,
                onToggleExpanded
            }
        });

        expect(screen.queryByRole('slider')).not.toBeInTheDocument();
        await fireEvent.click(screen.getByRole('button', { name: 'score' }));
        expect(onToggleExpanded).toHaveBeenCalledOnce();
    });

    it('shows the checkbox state and summary it is given', () => {
        render(MetadataFilterItem, {
            props: {
                metadataKey: 'score',
                bound: { min: 0, max: 10 },
                value: { min: 2, max: 5 },
                onValueCommit: vi.fn(),
                checked: true,
                summary: '2 – 5',
                onClear: vi.fn(),
                expanded: false,
                onToggleExpanded: vi.fn()
            }
        });

        expect(screen.getByRole('checkbox', { name: 'score filter' })).toBeChecked();
        expect(screen.getByText('2 – 5')).toBeInTheDocument();
    });
});
