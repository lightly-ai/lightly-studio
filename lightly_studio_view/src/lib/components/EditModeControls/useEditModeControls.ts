import { get, writable } from 'svelte/store';
import { toast } from 'svelte-sonner';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { usePostHog } from '$lib/hooks/usePostHog';

export type EditModeTrigger = 'click' | 'keyboard_shortcut';

// The app header and the fullscreen workspace header undo from the same history.
// An undo stays in the history until it is complete, so a second undo must wait.
const isUndoing = writable(false);

/** Starts and finishes editing, and undoes the latest edit. */
export function useEditModeControls(getCollectionId: () => string) {
    const { isEditingMode, setIsEditingMode, reversibleActions, executeReversibleAction } =
        useGlobalStorage();
    const { trackEvent } = usePostHog();

    const setEditMode = (active: boolean, triggeredBy: EditModeTrigger) => {
        if (active) {
            trackEvent('edit_mode_started', {
                collection_id: getCollectionId(),
                triggered_by: triggeredBy
            });
        }
        setIsEditingMode(active);
    };

    const undo = async (triggeredBy: EditModeTrigger) => {
        const latestAction = get(reversibleActions)[0];
        if (!latestAction || get(isUndoing)) return;
        trackEvent('edit_undo', { collection_id: getCollectionId(), triggered_by: triggeredBy });
        isUndoing.set(true);
        try {
            await executeReversibleAction(latestAction.id);
        } catch {
            toast.error('Failed to undo. Please try again.');
        } finally {
            isUndoing.set(false);
        }
    };

    return { isEditingMode, reversibleActions, isUndoing, setEditMode, undo };
}
