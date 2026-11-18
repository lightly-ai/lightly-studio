import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import CuboidTargetChip from './CuboidTargetChip.svelte';

const defaultProps = { targetSource: 'labels', needsPick: false, blockedReason: null };

describe('CuboidTargetChip', () => {
    it('names the source new cuboids go to', () => {
        render(CuboidTargetChip, { props: defaultProps });

        expect(screen.getByText('New cuboids go to labels')).toBeInTheDocument();
        expect(screen.getByTestId('cuboid-target-chip')).toHaveAttribute('data-state', 'target');
    });

    it('warns while no source is picked', () => {
        render(CuboidTargetChip, {
            props: { ...defaultProps, targetSource: null, needsPick: true }
        });

        expect(screen.getByText('Pick where new annotations go.')).toBeInTheDocument();
        expect(screen.getByTestId('cuboid-target-chip')).toHaveAttribute('data-state', 'warning');
    });

    it('warns with the reason while cuboids cannot be created', () => {
        render(CuboidTargetChip, {
            props: {
                ...defaultProps,
                targetSource: null,
                blockedReason: 'Loading annotation sources…'
            }
        });

        expect(screen.getByText('Loading annotation sources…')).toBeInTheDocument();
        expect(screen.getByTestId('cuboid-target-chip')).toHaveAttribute('data-state', 'warning');
    });
});
