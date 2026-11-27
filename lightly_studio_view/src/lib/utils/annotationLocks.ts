import { AnnotationType, type AnnotationView } from '$lib/api/lightly_studio_local';

/** What one lock click covers: one row, one source group or the whole panel. */
export type LockScope = 'annotation' | 'source' | 'all';

type LockableAnnotation = Pick<AnnotationView, 'annotation_type'>;

interface ToggleLocksResult {
    lockedIds: Set<string>;
    /** Whether the toggle locked the ids. False when it unlocked them. */
    locked: boolean;
    /** The number of ids whose lock state changed. */
    count: number;
}

/** Whether the annotation shows a row lock. Brush strokes never touch boxes or classifications. */
export const isAnnotationLockable = (annotation: LockableAnnotation): boolean =>
    annotation.annotation_type !== AnnotationType.OBJECT_DETECTION &&
    annotation.annotation_type !== AnnotationType.CLASSIFICATION;

export const listLockableIds = (
    annotations: Pick<AnnotationView, 'sample_id' | 'annotation_type'>[]
): string[] => annotations.filter(isAnnotationLockable).map((annotation) => annotation.sample_id);

/** False for an empty scope, so a bulk lock never shows as locked with nothing to lock. */
export const areAllLocked = (ids: string[], lockedIds: Set<string>): boolean =>
    ids.length > 0 && ids.every((id) => lockedIds.has(id));

/** Unlocks all ids when all are locked. Otherwise locks them all. Other ids stay as they are. */
export const toggleLocks = (ids: string[], lockedIds: Set<string>): ToggleLocksResult => {
    const nextLockedIds = new Set(lockedIds);
    if (areAllLocked(ids, lockedIds)) {
        ids.forEach((id) => nextLockedIds.delete(id));
        return { lockedIds: nextLockedIds, locked: false, count: ids.length };
    }
    const unlockedIds = ids.filter((id) => !lockedIds.has(id));
    unlockedIds.forEach((id) => nextLockedIds.add(id));
    return { lockedIds: nextLockedIds, locked: true, count: unlockedIds.length };
};
