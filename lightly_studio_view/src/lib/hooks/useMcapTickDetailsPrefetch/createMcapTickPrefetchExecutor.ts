import { getTickIndexes } from './getTickIndexes';
import { createPrefetchQueue } from './prefetchQueue';
import { createPrefetchSession, discardPrefetchSession } from './prefetchSession';
import type {
    McapTickPrefetchExecutorParams,
    PrefetchRangesRequest,
    PrefetchSession
} from './types';

/** Creates the session coordinator for the MCAP prefetch queue. */
export function createMcapTickPrefetchExecutor({
    client,
    getDatasetId,
    getSequenceId,
    getDisplayFrameId,
    getTicks,
    onStateChange
}: McapTickPrefetchExecutorParams) {
    let session: PrefetchSession | undefined;
    const notify = (currentSession: PrefetchSession) => {
        if (session === currentSession) {
            onStateChange(currentSession.completed, currentSession.errors);
        }
    };
    const queue = createPrefetchQueue({
        client,
        getDatasetId,
        getSequenceId,
        getDisplayFrameId,
        getTicks,
        isCurrentSession: (candidate) => session === candidate,
        onStateChange: notify
    });

    const prefetchRanges = ({ requestId, ranges }: PrefetchRangesRequest): Promise<void> => {
        if (!session || session.requestId !== requestId) {
            const completed = new Set(session?.completed ?? []);
            discardPrefetchSession(session);
            session = createPrefetchSession(requestId);
            session.completed = completed;
            notify(session);
        }

        return queue.enqueue(session, getTickIndexes(ranges, getTicks().length));
    };

    const cancel = () => {
        discardPrefetchSession(session);
        session = undefined;
        onStateChange(new Set(), new Map());
    };

    return { cancel, prefetchRanges };
}
