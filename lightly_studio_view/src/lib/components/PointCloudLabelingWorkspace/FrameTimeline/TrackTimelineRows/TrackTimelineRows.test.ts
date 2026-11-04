import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import TrackTimelineRows from './TrackTimelineRows.svelte';

const track = {
    object_track_id: 'track-1',
    object_track_number: 1,
    annotation_source_id: 'source',
    annotation_source_name: 'ground_truth',
    annotation_label_name: 'truck',
    annotations: [0, 1, 3].map((seq_number) => ({
        seq_number,
        annotation_id: `annotation-${seq_number}`,
        annotation_source_id: 'source',
        frame_id: 'odom',
        interpolated: seq_number === 1
    }))
};

const defaultProps = {
    ticks: [0, 1, 2, 3].map((seq_number) => ({ seq_number, timestamp_ns: null })),
    tracks: [track],
    selectedAnnotationId: null,
    onSelectAnnotation: vi.fn(),
    onSelectTick: vi.fn()
};

describe('TrackTimelineRows', () => {
    it('draws one run per stretch of drawn or generated annotations', () => {
        render(TrackTimelineRows, { props: defaultProps });

        const runs = screen.getAllByTitle(/^Frames? \d/);
        expect(runs.map((run) => run.getAttribute('title'))).toEqual([
            'Frame 1 · drawn',
            'Frame 2 · generated',
            'Frame 4 · drawn'
        ]);
    });

    it('selects the annotation of the clicked tick', async () => {
        const onSelectTick = vi.fn();
        const onSelectAnnotation = vi.fn();
        render(TrackTimelineRows, {
            props: { ...defaultProps, onSelectTick, onSelectAnnotation }
        });
        const row = screen.getByLabelText('Select truck track 1 position');
        vi.spyOn(row, 'getBoundingClientRect').mockReturnValue({
            left: 0,
            width: 400
        } as DOMRect);

        await fireEvent.click(row, { clientX: 350 });

        expect(onSelectTick).toHaveBeenCalledWith(3);
        expect(onSelectAnnotation).toHaveBeenCalledWith('annotation-3');
    });

    it('offers to start a track only when a cuboid can start one, even without tracks', async () => {
        const onStartTrack = vi.fn();
        const { rerender } = render(TrackTimelineRows, {
            props: { ...defaultProps, tracks: [] }
        });
        expect(screen.queryByText('Start track from selected cuboid')).toBeNull();

        await rerender({ ...defaultProps, tracks: [], onStartTrack });
        await fireEvent.click(screen.getByText('Start track from selected cuboid'));

        expect(onStartTrack).toHaveBeenCalledOnce();
    });
});
