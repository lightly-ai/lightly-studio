import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import type { CuboidAnnotation } from '../domain';
import TrackEditingControls from './TrackEditingControls.svelte';

const { start, extend } = vi.hoisted(() => ({
    start: vi.fn().mockResolvedValue('track-1'),
    extend: vi.fn().mockResolvedValue(undefined)
}));

vi.mock('./useTrackEditing.svelte', () => ({
    useTrackEditing: () => ({ start, extend, saving: false })
}));

const cuboid = {
    id: 'cuboid-2',
    trackId: null,
    annotationClassId: 'truck',
    annotationSourceId: 'ground-truth'
} as CuboidAnnotation;
const ticks = [2, 5, 9].map((seq_number) => ({ seq_number, timestamp_ns: null }));

describe('TrackEditingControls', () => {
    it('starts a track from the selected cuboid', async () => {
        const onTrackStarted = vi.fn();
        render(TrackEditingControls, {
            props: {
                datasetId: 'dataset',
                sequenceId: 'sequence',
                currentTick: 2,
                ticks,
                selectedCuboid: cuboid,
                onTrackStarted,
                onSaved: vi.fn()
            }
        });

        await fireEvent.click(screen.getByRole('button', { name: 'Start track' }));
        expect(start).toHaveBeenCalledWith('cuboid-2');
        expect(onTrackStarted).toHaveBeenCalledWith('track-1');
    });

    it('offers a chosen fill mode for a later keyframe', async () => {
        render(TrackEditingControls, {
            props: {
                datasetId: 'dataset',
                sequenceId: 'sequence',
                currentTick: 9,
                ticks,
                selectedCuboid: cuboid,
                selectedTrack: {
                    object_track_id: 'track-1',
                    object_track_number: 1,
                    managed: true,
                    annotations: [{ annotation_id: 'cuboid-1', seq_number: 2, interpolated: false }]
                },
                onTrackStarted: vi.fn(),
                onSaved: vi.fn()
            }
        });
        vi.spyOn(window, 'confirm').mockReturnValue(true);
        await fireEvent.change(screen.getByLabelText('Fill'), { target: { value: 'hold' } });
        await fireEvent.click(screen.getByRole('button', { name: 'Add keyframe to track 1' }));
        expect(extend).toHaveBeenCalledWith('track-1', 'cuboid-2', 'hold');
        expect(window.confirm).toHaveBeenCalled();
        vi.restoreAllMocks();
    });
});
