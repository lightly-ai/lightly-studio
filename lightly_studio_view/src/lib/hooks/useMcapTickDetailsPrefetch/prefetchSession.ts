import { createConcurrencyLimiter } from './createConcurrencyLimiter';
import type { PrefetchSession } from './types';

// The server decodes the camera frames of one video GOP in order, so consecutive tick-data
// requests wait for each other. Two at once overlap the point clouds of one tick with the
// cameras of the next. More only add waiting time to each request.
const MAX_CONCURRENT_TICK_DATA_REQUESTS = 2;

/** Creates an empty prefetch session for one buffering plan. */
export function createPrefetchSession(requestId: string, scopeKey = ''): PrefetchSession {
    return {
        requestId,
        scopeKey,
        completed: new Set(),
        queued: [],
        pending: new Map(),
        inFlight: 0,
        errors: new Map(),
        dataLimiter: createConcurrencyLimiter(MAX_CONCURRENT_TICK_DATA_REQUESTS)
    };
}

/** Discards queued work while allowing in-flight requests to finish in the background. */
export function discardPrefetchSession(session: PrefetchSession | undefined): void {
    if (!session) return;
    session.queued = [];
    session.dataLimiter.clear();
    for (const pending of session.pending.values()) pending.resolve();
    session.pending.clear();
}
