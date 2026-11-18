/**
 * Track when the grid reloads, that is refetches its current query (not the next page).
 * Feed it the reload state on every change; it returns the reload's start time (ms) once
 * the reload finishes, and null otherwise.
 */
export const trackGridReload = () => {
    let startedAt: number | null = null;
    return (reloading: boolean, now: number): number | null => {
        if (reloading) {
            startedAt ??= now;
            return null;
        }
        const finished = startedAt;
        startedAt = null;
        return finished;
    };
};
