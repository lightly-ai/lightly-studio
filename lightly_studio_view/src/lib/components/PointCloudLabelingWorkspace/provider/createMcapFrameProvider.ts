import { createPointCloudFrame } from '../domain';
import { FrameCache } from './frameCache';
import { frameIdentity, type FrameLocator, type McapSource } from './source';
import { WorkerClient } from './workerClient';
import type { WorkerCommand } from './workerProtocol';

interface ProviderOptions {
    source: McapSource;
    cacheBytes?: number;
    pointBudget?: number;
    createWorker?: ConstructorParameters<typeof WorkerClient>[0];
    onProgress?: (phase: string) => void;
    onTelemetry?: (event: {
        operation: 'load' | 'decode' | 'cache' | 'failure';
        durationMs: number;
        cacheBytes: number;
        bytesRead?: number;
        cacheHit?: boolean;
    }) => void;
}

/** Source adapter boundary: callers resolve sample metadata before creating a provider. */
export function createMcapFrameProvider(options: ProviderOptions) {
    const source = structuredClone(options.source);
    const client = new WorkerClient(options.createWorker);
    const cache = new FrameCache(options.cacheBytes ?? 32 * 1024 * 1024);
    const pointBudget = options.pointBudget ?? 350_000;
    let active: AbortController | undefined;
    let opened = false;
    let disposed = false;

    function cancel() {
        if (active) {
            active.abort();
            active = undefined;
            opened = false;
        }
    }

    async function request(command: WorkerCommand, signal: AbortSignal) {
        const result = await client.request(command, signal, (phase) =>
            options.onProgress?.(phase)
        );
        options.onTelemetry?.({
            operation: command.kind === 'frame' ? 'decode' : 'load',
            durationMs: result.durationMs ?? 0,
            cacheBytes: cache.bytes,
            bytesRead: result.bytesRead
        });
        return result;
    }

    /** Cancelled work is not a failure: only unexpected errors reset the session. */
    function fail(signal: AbortSignal, started: number) {
        if (signal.aborted) return;
        opened = false;
        client.dispose();
        options.onProgress?.('error');
        options.onTelemetry?.({
            operation: 'failure',
            durationMs: performance.now() - started,
            cacheBytes: cache.bytes
        });
    }

    async function run<T>(
        work: (signal: AbortSignal) => Promise<T>,
        signal?: AbortSignal
    ): Promise<T> {
        if (disposed) throw new Error('The MCAP frame provider has been disposed.');
        cancel();
        const controller = new AbortController();
        active = controller;
        controller.signal.addEventListener(
            'abort',
            () => {
                opened = false;
            },
            { once: true }
        );
        const abort = () => controller.abort(signal?.reason);
        signal?.addEventListener('abort', abort, { once: true });
        if (signal?.aborted) abort();
        const started = performance.now();
        try {
            controller.signal.throwIfAborted();
            const result = await work(controller.signal);
            controller.signal.throwIfAborted();
            options.onProgress?.('ready');
            return result;
        } catch (error) {
            fail(controller.signal, started);
            throw error;
        } finally {
            signal?.removeEventListener('abort', abort);
            if (active === controller) active = undefined;
        }
    }

    async function ensureOpen(signal: AbortSignal) {
        if (!opened) {
            await request({ kind: 'open', source }, signal);
            signal.throwIfAborted();
            opened = true;
        }
    }

    async function readFrame(locator: FrameLocator, signal: AbortSignal) {
        const key = JSON.stringify([source.version, frameIdentity(source, locator), pointBudget]);
        const cached = cache.get(key);
        options.onTelemetry?.({
            operation: 'cache',
            durationMs: 0,
            cacheBytes: cache.bytes,
            cacheHit: !!cached
        });
        if (cached) return cached;
        await ensureOpen(signal);
        const result = await request({ kind: 'frame', locator, pointBudget }, signal);
        signal.throwIfAborted();
        if (!result.frame) throw new Error('The worker returned no point-cloud frame.');
        const frame = createPointCloudFrame(result.frame);
        cache.set(key, frame);
        return frame;
    }

    return {
        open: (signal?: AbortSignal) =>
            run(async (current) => {
                const result = await request({ kind: 'open', source }, current);
                opened = true;
                return result.metadata;
            }, signal),
        loadFrame: (locator: FrameLocator, signal?: AbortSignal) =>
            run((current) => readFrame(locator, current), signal),
        /** Caller supplies nearby locators from the current timeline window; at most 4 are loaded. */
        prefetch: (nearby: readonly FrameLocator[], signal?: AbortSignal) =>
            run(async (current) => {
                for (const locator of nearby.slice(0, 4)) {
                    current.throwIfAborted();
                    await readFrame(locator, current);
                }
            }, signal),
        listFrames: (
            range: { channelId: number; startTimeNs: string; endTimeNs: string; limit?: number },
            signal?: AbortSignal
        ) =>
            run(async (current) => {
                await ensureOpen(current);
                return (
                    await request({ kind: 'range', ...range, limit: range.limit ?? 1000 }, current)
                ).range;
            }, signal),
        cancel,
        dispose: () => {
            cancel();
            client.dispose();
            cache.clear();
            disposed = true;
        }
    };
}
