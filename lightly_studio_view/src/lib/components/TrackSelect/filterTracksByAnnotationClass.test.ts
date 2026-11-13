import { describe, it, expect } from 'vitest';
import type { TrackWithClassNameView } from '$lib/api/lightly_studio_local';
import { filterTracksByAnnotationClass } from './filterTracksByAnnotationClass';

const tracks: TrackWithClassNameView[] = [
    { object_track_id: 't-1', object_track_number: 1, annotation_class_name: 'person' },
    { object_track_id: 't-2', object_track_number: 2, annotation_class_name: 'car' },
    { object_track_id: 't-3', object_track_number: 3, annotation_class_name: null }
];

describe('filterTracksByAnnotationClass', () => {
    it('keeps only tracks matching the annotation class and classless tracks', () => {
        const result = filterTracksByAnnotationClass(tracks, 'person');
        expect(result.map((t) => t.object_track_id)).toEqual(['t-1', 't-3']);
    });

    it('returns all tracks when annotationClassName is null', () => {
        const result = filterTracksByAnnotationClass(tracks, null);
        expect(result).toEqual(tracks);
    });
});
