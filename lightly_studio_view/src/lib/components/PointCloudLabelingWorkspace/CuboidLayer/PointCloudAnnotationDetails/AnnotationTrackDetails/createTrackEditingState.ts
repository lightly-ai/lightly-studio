import { derived, get, readonly, writable, type Readable } from 'svelte/store';

interface Params {
    refresh: () => Promise<void>;
}

interface TrackEditingState {
    isSaving: Readable<boolean>;
    needsRefresh: Readable<boolean>;
    disabled: Readable<boolean>;
    error: Readable<string | null>;
    save: (update: () => Promise<void>) => Promise<void>;
    retryRefresh: () => Promise<void>;
}

/** Keeps edits blocked after a successful save until fresh annotation state arrives. */
export function createTrackEditingState({ refresh }: Params): TrackEditingState {
    const isSaving = writable(false);
    const needsRefresh = writable(false);
    const error = writable<string | null>(null);
    const disabled = derived([isSaving, needsRefresh], (values) => values.some(Boolean));

    async function retryRefresh(): Promise<void> {
        isSaving.set(true);
        error.set(null);
        try {
            await refresh();
            needsRefresh.set(false);
        } catch {
            error.set('Track changes saved, but the workspace could not refresh.');
        } finally {
            isSaving.set(false);
        }
    }

    async function save(update: () => Promise<void>): Promise<void> {
        if (get(disabled)) return;
        isSaving.set(true);
        error.set(null);
        try {
            await update();
            needsRefresh.set(true);
        } catch {
            error.set('Failed to save track changes. Please try again.');
            isSaving.set(false);
            return;
        }
        await retryRefresh();
    }

    return {
        isSaving: readonly(isSaving),
        needsRefresh: readonly(needsRefresh),
        disabled,
        error: readonly(error),
        save,
        retryRefresh
    };
}
