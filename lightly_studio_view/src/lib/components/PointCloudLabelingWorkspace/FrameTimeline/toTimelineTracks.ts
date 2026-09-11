import type { AnnotationTrack, CuboidAnnotation } from '../domain';
import type { TimelineKeyframe, TimelineTrack } from '../types';

export interface ToTimelineTracksParams {
    /** Object tracks for the active recording, e.g. from `WorkspaceFixture.track` or persistence. */
    tracks: readonly AnnotationTrack[];
    /** Every loaded annotation; only those referencing one of `tracks` contribute a lane. */
    annotations: readonly CuboidAnnotation[];
    /** Frame position for every frame ID `FrameNavigation` has discovered so far. */
    framePositionById: ReadonlyMap<string, number>;
    /** Display name per annotation class ID. Falls back to the track ID when absent. */
    classNameById?: ReadonlyMap<string, string>;
    /** Lane/marker color per annotation class ID. */
    classColorById?: ReadonlyMap<string, string>;
}

/**
 * Adapts domain track and annotation data into the plain, position-keyed shape
 * `FrameTimeline` draws.
 *
 * Annotations or keyframes referencing a frame ID outside `framePositionById` are dropped
 * rather than guessed at: a frame the timeline has not discovered yet has no position to draw
 * at, so its geometry becomes visible once navigation reaches it.
 */
export function toTimelineTracks(params: ToTimelineTracksParams): TimelineTrack[] {
    const { tracks, annotations, framePositionById, classNameById, classColorById } = params;

    return tracks.map((track) => {
        const trackAnnotations = annotations.filter(
            (annotation) => annotation.trackId === track.id
        );
        const presentFramePositions = uniqueSortedPositions(
            trackAnnotations.map((annotation) => framePositionById.get(annotation.frameId))
        );
        const keyframes = toTimelineKeyframes(track, framePositionById);

        return {
            id: track.id,
            label: classNameById?.get(track.annotationClassId) ?? track.annotationClassId,
            color: classColorById?.get(track.annotationClassId),
            keyframes,
            presentFramePositions
        };
    });
}

function toTimelineKeyframes(
    track: AnnotationTrack,
    framePositionById: ReadonlyMap<string, number>
): TimelineKeyframe[] {
    return track.keyframes
        .map((keyframe) => {
            const framePosition = framePositionById.get(keyframe.frameId);
            return framePosition === undefined ? null : { id: keyframe.id, framePosition };
        })
        .filter((keyframe): keyframe is TimelineKeyframe => keyframe !== null)
        .sort((a, b) => a.framePosition - b.framePosition);
}

function uniqueSortedPositions(positions: readonly (number | undefined)[]): number[] {
    const known = positions.filter((position): position is number => position !== undefined);
    return [...new Set(known)].sort((a, b) => a - b);
}
