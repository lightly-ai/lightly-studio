import { browser } from '$app/environment';
import { writable, type Readable } from 'svelte/store';
import { getOperatorRunProgress, type OperatorProgress } from '$lib/api/lightly_studio_local';

const POLL_INTERVAL_MS = 500;

interface UseOperatorProgressReturn {
    progress: Readable<OperatorProgress | null>;
    startPolling: (runId: string) => void;
    stopPolling: () => void;
}

/**
 * Polls the progress of an in-flight operator run.
 *
 * The execute request blocks until the operator finishes, so progress is read
 * from a separate endpoint while that request is still pending. The backend
 * answers with 404 until the operator reports for the first time and again once
 * the run is done, which both surface here as `null`.
 */
export function useOperatorProgress(): UseOperatorProgressReturn {
    const progress = writable<OperatorProgress | null>(null);
    let intervalId: ReturnType<typeof setInterval> | undefined;

    const stopPolling = () => {
        if (intervalId !== undefined) {
            clearInterval(intervalId);
            intervalId = undefined;
        }
        progress.set(null);
    };

    const startPolling = (runId: string) => {
        // Guard against SSR, where there is no request to poll alongside.
        if (!browser) return;
        stopPolling();
        intervalId = setInterval(async () => {
            try {
                const response = await getOperatorRunProgress({ path: { run_id: runId } });
                progress.set(response.data ?? null);
            } catch {
                // A failed poll is not worth surfacing: the execute request owns
                // error reporting, and the next tick may well succeed.
                progress.set(null);
            }
        }, POLL_INTERVAL_MS);
    };

    return { progress, startPolling, stopPolling };
}
