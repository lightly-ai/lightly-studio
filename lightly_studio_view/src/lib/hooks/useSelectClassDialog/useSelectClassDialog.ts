import { writable, type Writable } from 'svelte/store';

/** Public surface of {@link useSelectClassDialog}. */
export type SelectClassDialog = {
    /** Reactive flag to bind to `<SelectClassDialog bind:open>`. */
    open: Writable<boolean>;
    /** Opens the dialog and resolves with the chosen label, or `null` if cancelled. */
    requestLabel: () => Promise<string | null>;
    /** Wire to the dialog's `onConfirm`. */
    handleConfirm: (label: string) => void;
    /** Wire to the dialog's `onCancel`. */
    handleCancel: () => void;
};

/**
 * Hook for managing the state of a "select class" dialog.
 */
export function useSelectClassDialog(): SelectClassDialog {
    const open = writable<boolean>(false);

    let pendingRequest: Promise<string | null> | null = null;
    let resolveRequest: ((label: string | null) => void) | null = null;

    const requestLabel = (): Promise<string | null> => {
        if (pendingRequest) return pendingRequest;

        open.set(true);
        pendingRequest = new Promise<string | null>((resolve) => {
            resolveRequest = resolve;
        });
        return pendingRequest;
    };

    // Close the dialog and deliver the result to every awaiter.
    const settle = (label: string | null) => {
        open.set(false);
        resolveRequest?.(label);
        resolveRequest = null;
        pendingRequest = null;
    };

    return {
        open,
        requestLabel,
        handleConfirm: (label) => settle(label),
        handleCancel: () => settle(null)
    };
}
