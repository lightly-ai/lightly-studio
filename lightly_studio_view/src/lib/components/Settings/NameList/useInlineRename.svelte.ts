interface UseInlineRenameParams {
    name: string;
    /** Saves the new name. A rejection is reported by the caller; the row keeps the old name. */
    onRename: (name: string) => Promise<unknown>;
}

/**
 * The rename of a row in place: start it, type a draft, save it on Enter or blur, drop it on
 * Escape. The input is inside the settings form, so Enter must not submit the form.
 */
export const useInlineRename = (getParams: () => UseInlineRenameParams) => {
    let isRenaming = $state(false);
    let draft = $state('');

    const start = () => {
        draft = getParams().name;
        isRenaming = true;
    };
    const save = async () => {
        if (!isRenaming) return;
        isRenaming = false;
        const { name, onRename } = getParams();
        const trimmed = draft.trim();
        if (!trimmed || trimmed === name) return;
        try {
            await onRename(trimmed);
        } catch {
            // The caller already reports the failure.
        }
    };
    const onKeyDown = (event: KeyboardEvent) => {
        // Enter and Escape during IME composition belong to the input method. Safari sends
        // the Enter that confirms the text with isComposing false and keyCode 229.
        if (event.isComposing || event.keyCode === 229) return;
        if (event.key === 'Enter') {
            event.preventDefault();
            save();
        } else if (event.key === 'Escape') {
            event.preventDefault();
            event.stopPropagation();
            isRenaming = false;
        }
    };

    return {
        get isRenaming() {
            return isRenaming;
        },
        get draft() {
            return draft;
        },
        set draft(value: string) {
            draft = value;
        },
        start,
        save,
        onKeyDown
    };
};
