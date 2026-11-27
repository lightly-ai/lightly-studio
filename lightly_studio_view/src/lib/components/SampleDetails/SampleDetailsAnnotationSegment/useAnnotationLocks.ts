import { useAnnotationLabelContext, usePostHog } from '$lib/hooks';
import { areAllLocked, toggleLocks, type LockScope } from '$lib/utils';

interface UseAnnotationLocksParams {
    getCollectionId: () => string;
}

interface UseAnnotationLocksReturn {
    isLocked: (annotationId: string) => boolean;
    /** Whether every id is locked. False for no ids. */
    areAllLocked: (ids: string[]) => boolean;
    /** Unlocks the ids when all are locked, otherwise locks them all. */
    toggle: (ids: string[], scope: LockScope) => void;
}

/**
 * Locks of the annotations of the current sample. A locked mask is protected from brush and SLIC
 * strokes. The callers pass lockable annotation ids only, see `listLockableIds`. Call during
 * component init: it reads the annotation label context.
 */
export const useAnnotationLocks = ({
    getCollectionId
}: UseAnnotationLocksParams): UseAnnotationLocksReturn => {
    const { context, setLockedAnnotationIds } = useAnnotationLabelContext();
    const { trackEvent } = usePostHog();

    const getLockedIds = () => context.lockedAnnotationIds ?? new Set<string>();

    return {
        isLocked: (annotationId) => getLockedIds().has(annotationId),
        areAllLocked: (ids) => areAllLocked(ids, getLockedIds()),
        toggle: (ids, scope) => {
            const { lockedIds, locked, count } = toggleLocks(ids, getLockedIds());
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
