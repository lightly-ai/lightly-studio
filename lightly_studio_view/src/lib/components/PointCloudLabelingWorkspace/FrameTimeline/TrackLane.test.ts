import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import TrackLane from './TrackLane.svelte';
import type { TimelineTrack } from '../types';

function track(overrides: Partial<TimelineTrack> = {}): TimelineTrack {
    return {
        id: 'track-0',
        label: 'Vehicle',
        keyframes: [{ id: 'keyframe-0', framePosition: 0 }],
        presentFramePositions: [0],
        ...overrides
    };
}

describe('TrackLane', () => {
    it('reports its id when the label is clicked', async () => {
        const onSelect = vi.fn();
        render(TrackLane, { props: { track: track(), frameCount: 3, onSelect } });

        await screen.getByRole('button', { name: 'Vehicle' }).click();

        expect(onSelect).toHaveBeenCalledWith('track-0');
    });

    it('marks the label pressed when selected', () => {
        render(TrackLane, { props: { track: track(), frameCount: 3, selected: true } });

        expect(screen.getByRole('button', { name: 'Vehicle' })).toHaveAttribute(
            'aria-pressed',
            'true'
        );
    });

    it('adds a keyframe at the active frame when requested', async () => {
        const onAddKeyframe = vi.fn();
        render(TrackLane, {
            props: {
                track: track(),
                frameCount: 3,
                activeFramePosition: 1,
                onAddKeyframe
            }
        });

        await screen.getByRole('button', { name: /add keyframe/i }).click();

        expect(onAddKeyframe).toHaveBeenCalledWith('track-0', 1);
    });

    it('disables adding a keyframe where one already exists', () => {
        render(TrackLane, {
            props: {
                track: track(),
                frameCount: 3,
                activeFramePosition: 0,
                onAddKeyframe: vi.fn()
            }
        });

        expect(screen.getByRole('button', { name: /add keyframe/i })).toBeDisabled();
    });

    it('removes the keyframe under its delete affordance', async () => {
        const onRemoveKeyframe = vi.fn();
        render(TrackLane, {
            props: { track: track(), frameCount: 3, onRemoveKeyframe }
        });

        await screen.getByRole('button', { name: /remove keyframe/i }).click();

        expect(onRemoveKeyframe).toHaveBeenCalledWith('track-0', 'keyframe-0');
    });

    it('offers neither add nor remove affordances without their handlers', () => {
        render(TrackLane, { props: { track: track(), frameCount: 3 } });

        expect(screen.queryByRole('button', { name: /add keyframe/i })).not.toBeInTheDocument();
        expect(screen.queryByRole('button', { name: /remove keyframe/i })).not.toBeInTheDocument();
    });
});
