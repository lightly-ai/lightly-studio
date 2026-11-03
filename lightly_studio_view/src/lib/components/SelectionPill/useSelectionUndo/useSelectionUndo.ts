import { get, writable } from 'svelte/store';
import { toast } from 'svelte-sonner';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { isTyping } from '../selectionPill.helpers';

const UNDO_WINDOW_MS = 10_000;
const GROUP_ID = 'selection-pill';

interface PendingUndo {
    id: string;
    toastId: string | number;
}

interface OfferUndoInput {
    /** What changed, e.g. "Added 'a' to 9 items". */
    message: string;
    /** Reverts exactly what changed; throws on failure. */
    revert: () => Promise<void>;
}

// The undo the visible toast offers; Z runs it while no text field has focus.
const pending = writable<PendingUndo | null>(null);
let nextId = 0;

/**
 * Bulk selection edits go on the app's undo stack (the header Undo in edit mode) and show a
 * toast with Undo for 10 s.
 */
export function useSelectionUndo() {
    const { addReversibleAction, executeReversibleAction } = useGlobalStorage();

    async function undo(id: string) {
        const current = get(pending);
        if (current?.id === id) {
            toast.dismiss(current.toastId);
            pending.set(null);
        }
        await executeReversibleAction(id);
    }

    function offerUndo({ message, revert }: OfferUndoInput) {
        const id = `${GROUP_ID}-${Date.now()}-${nextId++}`;
        addReversibleAction({
            id,
            description: `Undo: ${message}`,
            execute: () => runRevert(revert),
            timestamp: new Date(),
            groupId: GROUP_ID
        });
        const clear = () => pending.update((p) => (p?.id === id ? null : p));
        const toastId = toast.success(message, {
            duration: UNDO_WINDOW_MS,
            action: { label: 'Undo', onClick: () => void undo(id) },
            onDismiss: clear,
            onAutoClose: clear
        });
        pending.set({ id, toastId });
    }

    /** Runs the offered undo on a plain Z. Returns true when it handled the key. */
    function handleUndoKey(event: KeyboardEvent): boolean {
        const current = get(pending);
        if (!current || event.repeat || event.key.toLowerCase() !== 'z') return false;
        if (event.ctrlKey || event.metaKey || event.altKey) return false;
        if (isTyping(event.target) || isTyping(document.activeElement)) return false;
        event.preventDefault();
        void undo(current.id);
        return true;
    }

    return { offerUndo, handleUndoKey };
}

async function runRevert(revert: () => Promise<void>) {
    try {
        await revert();
        toast.success('Undone');
    } catch {
        toast.error('Failed to undo.');
    }
}
