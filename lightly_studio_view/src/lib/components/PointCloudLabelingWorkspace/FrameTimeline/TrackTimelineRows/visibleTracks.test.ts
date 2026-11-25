import { describe, expect, it } from 'vitest';
import type { SequenceTrackView } from '$lib/api/lightly_studio_local/types.gen';
import {
    DEFAULT_VISIBLE_TRACK_COUNT,
    getDefaultTrackKeys,
    getTrackKey,
    selectVisibleTracks
} from './visibleTracks';

const makeTrack = (number: number): SequenceTrackView => ({
    object_track_id: `track-${number}`,
    object_track_number: number,
    annotation_source_id: 'source',
    annotation_source_name: 'ground_truth',
    annotation_label_name: 'truck',
    annotations: [
        {
            seq_number: 0,
            annotation_id: `annotation-${number}`,
            annotation_source_id: 'source',
            frame_id: 'odom',
            interpolated: false
        }
    ]
});
const tracks = Array.from({ length: 25 }, (_, index) => makeTrack(index + 1));

describe('visibleTracks', () => {
    it('shows the first tracks by default', () => {
        const visible = selectVisibleTracks(tracks, null, null);
        expect(visible).toHaveLength(DEFAULT_VISIBLE_TRACK_COUNT);
        expect(visible[0]).toBe(tracks[0]);
        expect(getDefaultTrackKeys(tracks)).toEqual(visible.map(getTrackKey));
    });

    it('follows an explicit selection and ignores keys of deleted tracks', () => {
        const selection = [getTrackKey(tracks[20]!), getTrackKey(tracks[3]!), 'gone-source'];
        const visible = selectVisibleTracks(tracks, selection, null);
        expect(visible.map((track) => track.object_track_number)).toEqual([4, 21]);
    });

    it('allows an empty selection', () => {
        expect(selectVisibleTracks(tracks, [], null)).toEqual([]);
    });

    it('includes the selected track in the default list', () => {
        const visible = selectVisibleTracks(tracks, null, 'annotation-17');
        expect(visible.map((track) => track.object_track_number)).toEqual([
            1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 17
        ]);
    });

    it('does not add the selected track to an explicit selection', () => {
        expect(selectVisibleTracks(tracks, [], 'annotation-17')).toEqual([]);
    });
});
