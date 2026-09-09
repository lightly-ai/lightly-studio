import { describe, expect, it, vi } from 'vitest';
import { WorkerClient } from './workerClient';
import type { WorkerRequest, WorkerResult } from './workerProtocol';

function setup(postMessage?: (message: WorkerRequest) => void) {
    const worker = {
        onmessage: null as ((event: MessageEvent<WorkerResult>) => void) | null,
        onerror: null as ((event: ErrorEvent) => void) | null,
        terminate: vi.fn(),
        postMessage: postMessage ?? vi.fn()
    };
    return { worker, client: new WorkerClient(() => worker) };
}

const open = { kind: 'open' as const, source: undefined as never };

describe('WorkerClient', () => {
    it('forwards progress phases without settling the request', async () => {
        const { worker, client } = setup();
        const onPhase = vi.fn();
        const pending = client.request(open, new AbortController().signal, onPhase);
        worker.onmessage!({
            data: { requestId: 1, phase: 'indexing' }
        } as MessageEvent<WorkerResult>);
        expect(onPhase).toHaveBeenCalledWith('indexing');
        worker.onmessage!({ data: { requestId: 1, durationMs: 5 } } as MessageEvent<WorkerResult>);
        expect(await pending).toMatchObject({ durationMs: 5 });
    });

    it('ignores results from superseded requests', async () => {
        const { worker, client } = setup();
        const pending = client.request(open, new AbortController().signal, vi.fn());
        worker.onmessage!({ data: { requestId: 99, durationMs: 1 } } as MessageEvent<WorkerResult>);
        worker.onmessage!({ data: { requestId: 1, durationMs: 2 } } as MessageEvent<WorkerResult>);
        expect(await pending).toMatchObject({ durationMs: 2 });
    });

    it('reports a crashed worker as an actionable source error and discards it', async () => {
        const { worker, client } = setup();
        const pending = client.request(open, new AbortController().signal, vi.fn());
        worker.onerror!(new ErrorEvent('error'));
        await expect(pending).rejects.toMatchObject({ name: 'ProviderError', code: 'source' });
        expect(worker.terminate).toHaveBeenCalled();
    });

    it('discards the worker when a command cannot be posted', async () => {
        const failure = new DOMException('could not be cloned', 'DataCloneError');
        const { worker, client } = setup(() => {
            throw failure;
        });
        await expect(client.request(open, new AbortController().signal, vi.fn())).rejects.toBe(
            failure
        );
        expect(worker.terminate).toHaveBeenCalled();
    });

    it('rejects an already aborted signal and refuses concurrent requests', async () => {
        const { worker, client } = setup();
        const aborted = AbortSignal.abort();
        await expect(client.request(open, aborted, vi.fn())).rejects.toMatchObject({
            name: 'AbortError'
        });
        const pending = client.request(open, new AbortController().signal, vi.fn());
        await expect(client.request(open, new AbortController().signal, vi.fn())).rejects.toThrow(
            /already running/
        );
        worker.onmessage!({ data: { requestId: 1 } } as MessageEvent<WorkerResult>);
        await pending;
    });
});
