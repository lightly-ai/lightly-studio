import type { TrackWithClassNameView } from '$lib/api/lightly_studio_local';

/** Excludes the current track and its descendants from possible parents. */
export function getParentTrackChoices(
    tracks: TrackWithClassNameView[],
    trackId: string | null
): TrackWithClassNameView[] {
    const excluded = new Set<string>(trackId ? [trackId] : []);
    const children = new Map<string, string[]>();
    for (const track of tracks) {
        const parentId = track.parent_object_track_id;
        if (!parentId) continue;
        children.set(parentId, [...(children.get(parentId) ?? []), track.object_track_id]);
    }
    const pending = [...excluded];
    for (const id of pending) {
        for (const childId of children.get(id) ?? []) {
            if (excluded.has(childId)) continue;
            excluded.add(childId);
            pending.push(childId);
        }
    }
    return tracks.filter((track) => !excluded.has(track.object_track_id));
}
