import type { SequenceTrackView } from '$lib/api/lightly_studio_local/types.gen';

/** How many tracks show before the user picks their own. */
export const DEFAULT_VISIBLE_TRACK_COUNT = 10;

/** Identifies one track of one annotation source, as the timeline lists it. */
export const getTrackKey = (track: SequenceTrackView) =>
    `${track.object_track_id}-${track.annotation_source_id}`;

/** The tracks shown when the user has made no choice: the first ones in list order. */
export function getDefaultTrackKeys(tracks: readonly SequenceTrackView[]): string[] {
    return tracks.slice(0, DEFAULT_VISIBLE_TRACK_COUNT).map(getTrackKey);
}

/**
 * The tracks the timeline lists. A chosen selection wins over the default, keys of deleted
 * tracks are dropped, and the track holding the selected annotation is always listed so the
 * selection never points at a hidden row.
 */
export function selectVisibleTracks(
    tracks: readonly SequenceTrackView[],
    selection: readonly string[] | null,
    selectedAnnotationId: string | null
): SequenceTrackView[] {
    const chosen = new Set(selection ?? getDefaultTrackKeys(tracks));
    return tracks.filter(
        (track) =>
            chosen.has(getTrackKey(track)) ||
            track.annotations.some(({ annotation_id }) => annotation_id === selectedAnnotationId)
    );
}
