import { fireEvent, render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import type { SequenceTrackView, TickView } from '$lib/api/lightly_studio_local/types.gen';
import { getColorByLabel } from '$lib/utils';
import TrackTimelineRows from './TrackTimelineRows.svelte';
import { buildTrackTimeline } from './buildTrackTimeline';

const ticks: TickView[] = [2, 5, 9, 12].map((seq_number) => ({
    seq_number,
    timestamp_ns: null
}));
const track: SequenceTrackView = {
    object_track_id: 'track-1',
    object_track_number: 7,
    managed: false,
    annotation_label_name: 'truck',
    annotations: [
        { annotation_id: 'a', seq_number: 2, interpolated: false },
        { annotation_id: 'b', seq_number: 5, interpolated: true },
        { annotation_id: 'c', seq_number: 12, interpolated: false }
    ]
};

describe('TrackTimelineRows', () => {
    it('places sparse sequence numbers by tick order and leaves absent ticks blank', () => {
        expect(buildTrackTimeline(track, ticks).runs).toEqual([
            { startIndex: 0, endIndex: 0, interpolated: false },
            { startIndex: 1, endIndex: 1, interpolated: true },
            { startIndex: 3, endIndex: 3, interpolated: false }
        ]);
    });

    it('seeks through keyframes and shows all track rows', async () => {
        const onSelectTick = vi.fn();
        render(TrackTimelineRows, {
            props: {
                ticks,
                tracks: [
                    track,
                    {
                        object_track_id: 'track-2',
                        object_track_number: 8,
                        managed: false,
                        annotation_label_name: 'person',
                        annotations: [{ annotation_id: 'd', seq_number: 9, interpolated: false }]
                    }
                ],
                currentTick: 5,
                onSelectTick
            }
        });

        expect(screen.getByRole('button', { name: 'person · Track 8' })).toBeInTheDocument();
        const truckRow = screen.getByRole('button', { name: 'truck · Track 7' });
        expect(truckRow.querySelector('span')).toHaveStyle({
            backgroundColor: getColorByLabel('truck').color
        });
        expect(screen.getByTitle('Generated annotations')).toHaveStyle({
            backgroundColor: getColorByLabel('truck').color,
            opacity: '0.35'
        });
        await fireEvent.click(screen.getByRole('button', { name: 'Next keyframe' }));
        expect(onSelectTick).toHaveBeenCalledWith(12);
        await fireEvent.click(screen.getByRole('button', { name: 'Track 7 keyframe at frame 1' }));
        expect(onSelectTick).toHaveBeenCalledWith(2);
    });

    it('keeps a long track list accessible', () => {
        render(TrackTimelineRows, {
            props: {
                ticks,
                tracks: Array.from({ length: 30 }, (_, index) => ({
                    ...track,
                    object_track_id: `track-${index}`,
                    object_track_number: index + 1
                })),
                currentTick: 2,
                onSelectTick: vi.fn()
            }
        });

        expect(screen.getAllByRole('button', { name: /^truck · Track \d+$/ })).toHaveLength(30);
        expect(screen.getByRole('button', { name: 'truck · Track 30' })).toBeInTheDocument();
    });
});
