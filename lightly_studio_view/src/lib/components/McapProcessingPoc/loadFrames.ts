import type {
    McapSource,
    PointCloudFrame,
    WorkerRequest,
    WorkerResponse,
    WorkerSuccess
} from './types';

interface PendingRequest {
    resolve: (frame: PointCloudFrame) => void;
    reject: (error: Error) => void;
    startedAt: number;
}

const pending = new Map<number, PendingRequest>();
let worker: Worker | undefined;
let nextRequestId = 1;

/**
 * Loads a frame through the browser path, reusing one worker so that the summary index and the
 * schema readers are parsed once rather than on every run.
 */
export function loadBrowserFrame(
    source: McapSource,
    topic: string,
    timestampNs: string
): Promise<PointCloudFrame> {
    const request: WorkerRequest = {
        requestId: nextRequestId++,
        url: source.direct_url,
        sizeBytes: source.size_bytes,
        topic,
        timestampNs
    };
    return new Promise((resolve, reject) => {
        pending.set(request.requestId, { resolve, reject, startedAt: performance.now() });
        ensureWorker().postMessage(request);
    });
}

/** Terminates the worker so the next browser run measures a cold index parse. */
export function resetBrowserPath(): void {
    worker?.terminate();
    worker = undefined;
    rejectPending(new Error('The browser worker was reset.'));
}

/** Drops the server-side summary index so the next backend run measures a cold read. */
export async function resetBackendPath(): Promise<void> {
    const response = await fetch('/api/mcap-poc/reset', { method: 'POST' });
    if (!response.ok) throw new Error(await response.text());
}

export async function loadBackendFrame(
    topic: string,
    timestampNs: string
): Promise<PointCloudFrame> {
    const startedAt = performance.now();
    const query = new URLSearchParams({ topic, timestamp_ns: timestampNs });
    const response = await fetch(`/api/mcap-poc/frame?${query}`, { cache: 'no-store' });
    if (!response.ok) throw new Error(await response.text());
    const points = new Float32Array(await response.arrayBuffer());
    return {
        points,
        pointCount: headerNumber(response, 'X-MCAP-Point-Count'),
        logTimeNs: response.headers.get('X-MCAP-Log-Time-Ns') ?? '',
        metrics: {
            totalMs: performance.now() - startedAt,
            processingMs: headerNumber(response, 'X-MCAP-Backend-Wall-Ms'),
            indexMs: headerNumber(response, 'X-MCAP-Backend-Index-Ms'),
            decodeMs: headerNumber(response, 'X-MCAP-Backend-Decode-Ms'),
            bytesRead: headerNumber(response, 'X-MCAP-Source-Bytes'),
            requestCount: headerNumber(response, 'X-MCAP-Read-Count'),
            peakMemoryBytes: headerNumber(response, 'X-MCAP-Backend-Peak-Bytes'),
            indexCached: response.headers.get('X-MCAP-Index-Cached') === '1'
        }
    };
}

function ensureWorker(): Worker {
    if (worker) return worker;
    const created = new Worker(new URL('./mcap.worker.ts', import.meta.url), { type: 'module' });
    created.onmessage = (event: MessageEvent<WorkerResponse>) => settle(event.data);
    created.onerror = (event) => {
        resetBrowserPath();
        rejectPending(new Error(event.message));
    };
    worker = created;
    return created;
}

function settle(response: WorkerResponse): void {
    const request = pending.get(response.requestId);
    if (!request) return;
    pending.delete(response.requestId);
    if ('error' in response) return request.reject(new Error(response.error));
    request.resolve(toFrame(response, request.startedAt));
}

function toFrame(response: WorkerSuccess, startedAt: number): PointCloudFrame {
    return {
        points: new Float32Array(response.points),
        pointCount: response.pointCount,
        logTimeNs: response.logTimeNs,
        metrics: { ...response.metrics, totalMs: performance.now() - startedAt }
    };
}

function rejectPending(error: Error): void {
    for (const request of pending.values()) request.reject(error);
    pending.clear();
}

function headerNumber(response: Response, name: string): number {
    return Number(response.headers.get(name) ?? 0);
}
