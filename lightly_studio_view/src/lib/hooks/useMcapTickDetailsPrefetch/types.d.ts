import type { TickView } from '$lib/api/lightly_studio_local/types.gen';
import type { QueryClient } from '@tanstack/svelte-query';

export interface TickRange {
    /** Inclusive zero-based index of the first tick in the range. */
    startIndex: number;
    /** Inclusive zero-based index of the last tick in the range. */
    endIndex: number;
}

export interface McapTickDetailsPrefetchParams {
    /** Reactive dataset identifier. */
    getDatasetId: () => string;
    /** Reactive sequence identifier. */
    getSequenceId: () => string;
    /** Reactive target frame for point clouds and annotations. */
    getDisplayFrameId: () => string | undefined;
    /** Reactive ordered ticks used to translate ranges into sequence positions. */
    getTicks: () => TickView[];
}

export interface PrefetchRangesRequest {
    /** Identifies one buffering session; a new value discards the previous session. */
    requestId: string;
    /** Inclusive tick-index ranges to load in this request. */
    ranges: readonly TickRange[];
}

export interface PendingTick {
    /** Shared promise for callers waiting on the same pending tick. */
    promise: Promise<void>;
    /** Resolves when the tick request finishes, regardless of request success. */
    resolve: () => void;
}

export interface PrefetchSession {
    /** Session identifier used to discard obsolete buffering plans. */
    requestId: string;
    /** Cache scope whose completed ticks can be reused by a later request. */
    scopeKey: string;
    /** Completed tick indexes in the current session. */
    completed: Set<number>;
    /** Tick indexes waiting for a concurrency slot. */
    queued: number[];
    /** Tick indexes currently queued or in flight. */
    pending: Map<number, PendingTick>;
    /** Number of active prefetch requests. */
    inFlight: number;
    /** Errors from failed tick prefetches in the current session. */
    errors: Map<number, unknown>;
}

export interface McapTickPrefetchExecutorParams extends McapTickDetailsPrefetchParams {
    /** Query client that owns the visible workspace cache. */
    client: QueryClient;
    /** Called whenever completed ticks or errors change. */
    onStateChange: (completed: ReadonlySet<number>, errors: ReadonlyMap<number, unknown>) => void;
}

export interface McapTickPrefetchSchedulerParams extends McapTickDetailsPrefetchParams {
    /** Reactive flag controlling whether background buffering may start. */
    getEnabled?: () => boolean;
    /** Reactive identifier of the current buffering plan. */
    getRequestId: () => string;
    /** Reactive ranges to load in order. */
    getRanges: () => readonly TickRange[];
    /** Number of ticks sent to the executor per chunk. */
    getChunkSize?: () => number;
    /** Delay between completed chunks in milliseconds. */
    getDelayMs?: () => number;
}
