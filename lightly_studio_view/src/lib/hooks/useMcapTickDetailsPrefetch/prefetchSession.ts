import type { PrefetchSession } from './types';

/** Creates an empty prefetch session for one buffering plan. */
export function createPrefetchSession(requestId: string): PrefetchSession {
    return {
        requestId,
        completed: new Set(),
        queued: [],
        pending: new Map(),
        inFlight: 0,
        errors: new Map()
    };
}

/** Discards queued work while allowing in-flight requests to finish in the background. */
export function discardPrefetchSession(session: PrefetchSession | undefined): void {
    if (!session) return;
    session.queued = [];
    for (const pending of session.pending.values()) pending.resolve();
    session.pending.clear();
}
