import type { TickDetailView } from '$lib/api/lightly_studio_local/types.gen';
import type { CuboidAnnotation } from '../domain';

/** The fields that decide whether an annotation is hidden. */
export interface AnnotationVisibilityRef {
    annotationId: string;
    sourceId: string;
    trackId: string | null;
}

/** The sources and tracks the user hid in the workspace. */
export interface HiddenAnnotations {
    sourceIds: ReadonlySet<string>;
    trackKeys: ReadonlySet<string>;
}

/**
 * Identifies the track of an annotation across ticks. An untracked annotation is its own track,
 * so hiding it hides no other annotation.
 */
export function getTrackVisibilityKey({
    annotationId,
    sourceId,
    trackId
}: AnnotationVisibilityRef): string {
    return `${sourceId}:${trackId ?? annotationId}`;
}

/** True when the source or the track of the annotation is hidden. */
export function isAnnotationHidden(
    ref: AnnotationVisibilityRef,
    hidden: HiddenAnnotations
): boolean {
    return hidden.sourceIds.has(ref.sourceId) || hidden.trackKeys.has(getTrackVisibilityKey(ref));
}

/** True when a cuboid is selected and the user hid it. */
export function isSelectedCuboidHidden<T extends { id: string }>(
    selectedId: string | null,
    cuboids: readonly T[],
    isHidden: (cuboid: T) => boolean
): boolean {
    const selected = cuboids.find(({ id }) => id === selectedId);
    return selected !== undefined && isHidden(selected);
}

/** Returns a copy of the set with the key added, or removed when it is present. */
export function toggleSetEntry(set: ReadonlySet<string>, key: string): Set<string> {
    const next = new Set(set);
    if (next.has(key)) {
        next.delete(key);
    } else {
        next.add(key);
    }
    return next;
}

export function cuboidToVisibilityRef(
    cuboid: Pick<CuboidAnnotation, 'id' | 'annotationSourceId' | 'trackId'>
): AnnotationVisibilityRef {
    return {
        annotationId: cuboid.id,
        sourceId: cuboid.annotationSourceId,
        trackId: cuboid.trackId
    };
}

export function tickAnnotationToVisibilityRef(
    annotation: Pick<
        TickDetailView['annotations'][number],
        'sample_id' | 'annotation_collection_id' | 'object_track_id'
    >
): AnnotationVisibilityRef {
    return {
        annotationId: annotation.sample_id,
        sourceId: annotation.annotation_collection_id,
        trackId: annotation.object_track_id ?? null
    };
}
