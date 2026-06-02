import { writable, type Writable } from 'svelte/store';

interface SelectClassResult {
    /** The chosen (or newly typed) class label. */
    label: string;
    /** The chosen annotation source (collection name), if a source selector was shown. */
    source?: string;
}

interface SelectClassDialog {
    /** Reactive flag to bind to `<SelectClassDialog bind:open>`. */
    open: Writable<boolean>;
    /** Opens the dialog and resolves with the chosen class and source, or `null` if cancelled. */
    requestLabel: () => Promise<SelectClassResult | null>;
    /** Wire to the dialog's `onConfirm`. */
    handleConfirm: (label: string, source?: string) => void;
    /** Wire to the dialog's `onCancel`. */
    handleCancel: () => void;
}

/**
 * Hook for managing the state of a "select class" dialog.
 */
export function useSelectClassDialog(): SelectClassDialog {
    const open = writable<boolean>(false);

    let pendingRequest: Promise<SelectClassResult | null> | null = null;
    let resolveRequest: ((result: SelectClassResult | null) => void) | null = null;

    const requestLabel = (): Promise<SelectClassResult | null> => {
        open.set(true);
        if (pendingRequest) return pendingRequest;

        pendingRequest = new Promise<SelectClassResult | null>((resolve) => {
            resolveRequest = resolve;
        });
        return pendingRequest;
    };

    // Close the dialog and deliver the result to every awaiter.
    const settle = (result: SelectClassResult | null) => {
        open.set(false);
        resolveRequest?.(result);
        resolveRequest = null;
        pendingRequest = null;
    };

    return {
        open,
        requestLabel,
        handleConfirm: (label, source) => settle({ label, source }),
        handleCancel: () => settle(null)
    };
}
