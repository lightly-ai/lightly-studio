import { describe, expect, it } from 'vitest';
import { createPrefetchSession, discardPrefetchSession } from './prefetchSession';

describe('prefetchSession', () => {
    it('creates an empty session with its request id', () => {
        const session = createPrefetchSession('request-1');

        expect(session.requestId).toBe('request-1');
        expect(session.scopeKey).toBe('');
        expect(session.completed).toEqual(new Set());
        expect(session.queued).toEqual([]);
        expect(session.pending).toEqual(new Map());
        expect(session.inFlight).toBe(0);
        expect(session.errors).toEqual(new Map());
    });

    it('resolves and removes queued work when discarded', async () => {
        const session = createPrefetchSession('request-1');
        let resolved = false;
        let resolve!: () => void;
        const promise = new Promise<void>((complete) => (resolve = complete));
        promise.then(() => (resolved = true));
        session.queued = [1, 2];
        session.pending.set(1, { promise, resolve });

        discardPrefetchSession(session);
        await promise;

        expect(resolved).toBe(true);
        expect(session.queued).toEqual([]);
        expect(session.pending).toEqual(new Map());
    });
});
