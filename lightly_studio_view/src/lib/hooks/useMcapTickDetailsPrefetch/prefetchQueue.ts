import type { QueryClient } from '@tanstack/svelte-query';
import { prefetchMcapTick } from './prefetchMcapTick';
import type { McapTickDetailsPrefetchParams, PendingTick, PrefetchSession } from './types';

const MAX_CONCURRENT_PREFETCHES = 4;

interface PrefetchQueueParams extends McapTickDetailsPrefetchParams {
    /** Query client that owns the visible workspace cache. */
    client: QueryClient;
    /** Returns whether a session is still the active buffering session. */
    isCurrentSession: (session: PrefetchSession) => boolean;
    /** Publishes completed ticks and errors to the hook state. */
    onStateChange: (session: PrefetchSession) => void;
}

const enqueueIndexes = (session: PrefetchSession, indexes: number[]): Promise<void>[] => {
    const promises: Promise<void>[] = [];
    for (const index of indexes) {
        if (session.completed.has(index)) continue;
        const existing = session.pending.get(index);
        if (existing) {
            promises.push(existing.promise);
            continue;
        }

        let resolve!: () => void;
        const promise = new Promise<void>((complete) => (resolve = complete));
        session.pending.set(index, { promise, resolve });
        session.queued.push(index);
        promises.push(promise);
    }
    return promises;
};

/** Creates the bounded-concurrency queue for MCAP tick requests. */
export function createPrefetchQueue({
    client,
    getDatasetId,
    getSequenceId,
    getDisplayFrameId,
    getTicks,
    isCurrentSession,
    onStateChange
}: PrefetchQueueParams) {
    function pump(session: PrefetchSession): void {
        while (session.inFlight < MAX_CONCURRENT_PREFETCHES && session.queued.length > 0) {
            const index = session.queued.shift();
            if (index === undefined) return;
            const pending = session.pending.get(index);
            const tick = getTicks()[index];
            if (!pending || !tick) {
                pending?.resolve();
                session.pending.delete(index);
                continue;
            }

            session.inFlight += 1;
            void prefetchTick(session, index, pending, tick.seq_number);
        }
    }

    async function prefetchTick(
        session: PrefetchSession,
        index: number,
        pending: PendingTick,
        seqNumber: number
    ): Promise<void> {
        try {
            await prefetchMcapTick(client, {
                datasetId: getDatasetId(),
                sequenceId: getSequenceId(),
                seqNumber,
                displayFrameId: getDisplayFrameId()
            });
            session.completed.add(index);
            session.errors.delete(index);
        } catch (error: unknown) {
            session.errors.set(index, error);
        } finally {
            session.inFlight -= 1;
            session.pending.delete(index);
            pending.resolve();
            if (isCurrentSession(session)) onStateChange(session);
            pump(session);
        }
    }

    return {
        enqueue(session: PrefetchSession, indexes: number[]): Promise<void> {
            const promises = enqueueIndexes(session, indexes);
            pump(session);
            return Promise.all(promises).then(() => undefined);
        }
    };
}
