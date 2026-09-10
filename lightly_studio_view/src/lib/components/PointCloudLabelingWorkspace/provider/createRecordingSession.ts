import { createPointCloudFrame, type PointCloudFrame } from '../domain';
import type { FrameLocator, McapSource } from './source';
import { WorkerClient } from './workerClient';
import type { WorkerCommand, WorkerResult } from './workerProtocol';

const DEFAULT_POINT_BUDGET = 350_000;
const DEFAULT_FRAME_LIMIT = 1000;

const ignore = () => undefined;

/**
 * Copies a locator field by field before it crosses to the worker.
 *
 * Commands are structured-cloned, which fails on anything the caller happens to be holding
 * it in -- a Svelte deep state proxy, most easily. Naming the fields also keeps unrelated
 * properties out of the cache key the worker sees.
 */
function plain(locator: FrameLocator): FrameLocator {
    return {
        channelId: locator.channelId,
        logTimeNs: locator.logTimeNs,
        occurrence: locator.occurrence
    };
}

export type RecordingMetadata = NonNullable<WorkerResult['metadata']>;

export interface FrameRange {
    channelId: number;
    startTimeNs: string;
    endTimeNs: string;
    limit?: number;
}

export interface TelemetryEvent {
    operation: 'open' | 'list' | 'decode';
    durationMs: number;
    bytesRead?: number;
}

export interface SessionOptions {
    /** An already-resolved recording. Sessions never discover their own source. */
    source: McapSource;
    createWorker?: ConstructorParameters<typeof WorkerClient>[0];
    onProgress?: (phase: string) => void;
    onTelemetry?: (event: TelemetryEvent) => void;
}

/**
 * One open recording, with one job: turn a locator into a frame.
 *
 * Deliberately not a cache and not a scheduler. Which frames are worth holding, which
 * requests supersede which, and when a stale result should be dropped are decisions the
 * caller's query layer already makes for every other resource in the app; duplicating them
 * here is what made the earlier provider a state machine.
 *
 * Requests queue rather than pre-empt, so a background read cannot cancel a visible one.
 * Aborting a request that has not started yet costs nothing; aborting one in flight
 * terminates the worker, which is the only way to stop a synchronous decode, and costs the
 * parsed summary index with it.
 */
export interface RecordingSession {
    readonly source: McapSource;
    readonly metadata: RecordingMetadata;
    listFrames(range: FrameRange, signal?: AbortSignal): Promise<readonly FrameLocator[]>;
    readFrame(
        locator: FrameLocator,
        options?: { pointBudget?: number },
        signal?: AbortSignal
    ): Promise<PointCloudFrame>;
    dispose(): void;
}

/**
 * Opens a recording and reads its channel metadata.
 *
 * @param options - The resolved source, plus optional progress and timing sinks.
 * @returns A session bound to that recording. Dispose it to release the worker.
 * @throws ProviderError - The recording could not be opened, read, or indexed.
 */
export async function createRecordingSession(options: SessionOptions): Promise<RecordingSession> {
    const source = structuredClone(options.source);
    const client = new WorkerClient(options.createWorker);
    let queue: Promise<unknown> = Promise.resolve();

    async function request(
        command: WorkerCommand,
        operation: TelemetryEvent['operation'],
        signal: AbortSignal
    ): Promise<WorkerResult> {
        const result = await client.request(command, signal, (phase) =>
            options.onProgress?.(phase)
        );
        options.onTelemetry?.({
            operation,
            durationMs: result.durationMs ?? 0,
            bytesRead: result.bytesRead
        });
        return result;
    }

    /**
     * Serialises worker traffic: one command is in flight at a time, in call order.
     *
     * An abort settles the caller immediately, but the queued turn still checks the signal
     * when it comes up, so an abandoned request never reaches the worker and the parsed
     * summary index survives. Only a request already in flight has to terminate it.
     */
    function enqueue<T>(
        work: (signal: AbortSignal) => Promise<T>,
        signal: AbortSignal = new AbortController().signal
    ): Promise<T> {
        const turn = queue.then(() => {
            signal.throwIfAborted();
            return work(signal);
        });
        queue = turn.then(ignore, ignore);
        return new Promise<T>((resolve, reject) => {
            const abort = () => reject(signal.reason);
            signal.addEventListener('abort', abort, { once: true });
            void turn
                .then(resolve, reject)
                .finally(() => signal.removeEventListener('abort', abort));
        });
    }

    try {
        const opened = await enqueue((current) =>
            request({ kind: 'open', source }, 'open', current)
        );
        if (!opened.metadata) {
            throw new Error('The worker opened the recording without returning its metadata.');
        }
        const metadata = opened.metadata;

        return {
            source,
            metadata,
            listFrames: (range, signal) =>
                enqueue(async (current) => {
                    const command = {
                        kind: 'range' as const,
                        channelId: range.channelId,
                        startTimeNs: range.startTimeNs,
                        endTimeNs: range.endTimeNs,
                        limit: range.limit ?? DEFAULT_FRAME_LIMIT
                    };
                    const result = await request(command, 'list', current);
                    return result.range?.frames ?? [];
                }, signal),
            readFrame: (locator, frameOptions, signal) =>
                enqueue(async (current) => {
                    const pointBudget = frameOptions?.pointBudget ?? DEFAULT_POINT_BUDGET;
                    const result = await request(
                        { kind: 'frame', locator: plain(locator), pointBudget },
                        'decode',
                        current
                    );
                    if (!result.frame) {
                        throw new Error('The worker returned no point-cloud frame.');
                    }
                    return createPointCloudFrame(result.frame);
                }, signal),
            dispose: () => client.dispose()
        };
    } catch (error) {
        client.dispose();
        throw error;
    }
}
