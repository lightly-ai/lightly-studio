import type { AnnotationView } from '$lib/api/lightly_studio_local';
import { useAnnotationLabelContext, usePostHog } from '$lib/hooks';
import { areAllLocked, listLockableIds, toggleLocks, type LockScope } from '$lib/utils';

interface UseAnnotationLocksParams {
    getCollectionId: () => string;
}

interface UseAnnotationLocksReturn {
    isLocked: (annotationId: string) => boolean;
    hasLockable: (annotations: AnnotationView[]) => boolean;
    /** Whether every lockable annotation is locked. False when none is lockable. */
    areAllLocked: (annotations: AnnotationView[]) => boolean;
    /** Unlocks the lockable annotations when all are locked, otherwise locks them all. */
    toggle: (annotations: AnnotationView[], scope: LockScope) => void;
}

/**
 * Locks of the annotations of the current sample. A locked mask is protected from brush and SLIC
 * strokes. Call during component init: it reads the annotation label context.
 */
export const useAnnotationLocks = ({
    getCollectionId
}: UseAnnotationLocksParams): UseAnnotationLocksReturn => {
    const { context, setLockedAnnotationIds } = useAnnotationLabelContext();
    const { trackEvent } = usePostHog();

    const getLockedIds = () => context.lockedAnnotationIds ?? new Set<string>();

    return {
        isLocked: (annotationId) => getLockedIds().has(annotationId),
        hasLockable: (annotations) => listLockableIds(annotations).length > 0,
        areAllLocked: (annotations) => areAllLocked(listLockableIds(annotations), getLockedIds()),
        toggle: (annotations, scope) => {
            const { lockedIds, locked, count } = toggleLocks(
                listLockableIds(annotations),
                getLockedIds()
            );
            if (count === 0) return;
            setLockedAnnotationIds(lockedIds);
            trackEvent('annotation_lock_toggled', {
                collection_id: getCollectionId(),
                locked,
                scope,
                count
            });
        }
    };
};
