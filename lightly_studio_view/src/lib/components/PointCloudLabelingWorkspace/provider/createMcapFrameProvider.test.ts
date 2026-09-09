import { describe, expect, it, vi, type Mock } from 'vitest';
import { canonicalCoordinateFrame } from '../domain';
import { createMcapFrameProvider } from './index';
import { frameIdentity } from './source';
import type { WorkerRequest, WorkerResult } from './workerProtocol';

const source = {
    recordingId: 'r',
    version: 'v',
    url: '/source',
    sizeBytes: '100',
    coordinateFrame: canonicalCoordinateFrame('lidar'),
    logClockId: 'log',
    publishClockId: 'pub'
};
const locator = { channelId: 1, logTimeNs: '100', occurrence: 0 };

interface FakeWorker {
    onmessage: ((event: MessageEvent<WorkerResult>) => void) | null;
    onerror: ((event: ErrorEvent) => void) | null;
    terminate: Mock<() => void>;
    postMessage: (message: WorkerRequest) => void;
}

function setup(options: { fail?: WorkerResult['error'] } = {}) {
    const commands: WorkerRequest[] = [];
    let holdFrames = false;
    const workers: FakeWorker[] = [];
    function createWorker(): FakeWorker {
        const worker: FakeWorker = {
            onmessage: null,
            onerror: null,
            terminate: vi.fn(),
            postMessage: (message: WorkerRequest) => {
                commands.push(message);
                if (holdFrames && message.command.kind === 'frame') return;
                worker.onmessage?.({
                    data: {
                        requestId: message.requestId,
                        phase: message.command.kind === 'open' ? 'indexing' : 'decoding'
                    }
                } as MessageEvent<WorkerResult>);
                queueMicrotask(() => {
                    const result: WorkerResult = { requestId: message.requestId, durationMs: 1 };
                    if (options.fail) {
                        result.error = options.fail;
                        worker.onmessage?.({ data: result } as MessageEvent<WorkerResult>);
                        return;
                    }
                    if (message.command.kind === 'range')
                        result.range = {
                            frames: [{ channelId: 1, logTimeNs: '100', occurrence: 0 }],
                            truncated: true
                        };
                    if (message.command.kind === 'open')
                        result.metadata = { topics: [], firstLogTimeNs: null, lastLogTimeNs: null };
                    if (message.command.kind === 'frame')
                        result.frame = {
                            id: frameIdentity(source, message.command.locator),
                            source: {
                                recordingId: 'r',
                                streamId: '1',
                                messageId: 'm',
                                publishedAt: null
                            },
                            timestamp: { nanoseconds: '100', clockId: 'log' },
                            coordinateFrame: source.coordinateFrame,
                            sourcePointCount: 1,
                            positions: new Float32Array([1, 2, 3]),
                            cameras: []
                        };
                    worker.onmessage?.({ data: result } as MessageEvent<WorkerResult>);
                });
            }
        };
        workers.push(worker);
        return worker;
    }
    const onTelemetry = vi.fn();
    const onProgress = vi.fn();
    const provider = createMcapFrameProvider({ source, createWorker, onTelemetry, onProgress });
    return {
        provider,
        commands,
        workers,
        onTelemetry,
        onProgress,
        hold: () => {
            holdFrames = true;
        },
        release: () => {
            holdFrames = false;
        }
    };
}

describe('createMcapFrameProvider', () => {
    it('reuses cached canonical frames, prefetches neighbors, and emits timing events', async () => {
        const { provider, commands, onTelemetry } = setup();
        const first = await provider.loadFrame(locator);
        const exported = first.positions.copy();
        exported[0] = 99;
        expect(await provider.loadFrame(locator)).toBe(first);
        expect(first.positions.copy()[0]).toBe(1);
        const neighbor = { ...locator, occurrence: 1 };
        await provider.prefetch([neighbor]);
        await provider.loadFrame(neighbor);
        expect(commands.map((request) => request.command.kind)).toEqual(['open', 'frame', 'frame']);
        expect(onTelemetry).toHaveBeenCalledWith(
            expect.objectContaining({ operation: 'cache', cacheHit: true })
        );
        expect(onTelemetry).toHaveBeenCalledWith(
            expect.objectContaining({ operation: 'decode', durationMs: 1 })
        );
        provider.dispose();
        await expect(provider.loadFrame(locator)).rejects.toThrow(/disposed/);
    });

    it('terminates stale decoding and reopens the worker for a new request', async () => {
        const task = setup();
        await task.provider.open();
        task.hold();
        const stale = task.provider.loadFrame(locator);
        const rejected = expect(stale).rejects.toMatchObject({ name: 'AbortError' });
        await vi.waitFor(() => expect(task.commands.at(-1)?.command.kind).toBe('frame'));
        task.release();
        const fresh = await task.provider.loadFrame({ ...locator, occurrence: 1 });
        await rejected;
        expect(task.workers[0].terminate).toHaveBeenCalled();
        expect(task.workers.length).toBe(2);
        expect(fresh.id).toBe(frameIdentity(source, { ...locator, occurrence: 1 }));
        task.provider.dispose();
    });

    it('lists a bounded frame range from the indexed recording', async () => {
        const { provider, commands, onProgress } = setup();
        expect(
            await provider.listFrames({ channelId: 1, startTimeNs: '1', endTimeNs: '200' })
        ).toEqual({
            frames: [{ channelId: 1, logTimeNs: '100', occurrence: 0 }],
            truncated: true
        });
        expect(commands.map((request) => request.command.kind)).toEqual(['open', 'range']);
        expect(commands[1].command).toMatchObject({ limit: 1000 });
        await provider.listFrames({ channelId: 1, startTimeNs: '1', endTimeNs: '200', limit: 10 });
        expect(commands.at(-1)?.command).toMatchObject({ limit: 10 });
        expect(onProgress.mock.calls.flat()).toEqual([
            'indexing',
            'decoding',
            'ready',
            'decoding',
            'ready'
        ]);
        provider.dispose();
    });

    it('surfaces worker failures with progress and failure telemetry', async () => {
        const { provider, onProgress, onTelemetry, workers } = setup({
            fail: { code: 'schema', message: 'Select a supported channel.' }
        });
        await expect(provider.loadFrame(locator)).rejects.toMatchObject({
            name: 'ProviderError',
            code: 'schema'
        });
        expect(onProgress).toHaveBeenCalledWith('error');
        expect(onTelemetry).toHaveBeenCalledWith(
            expect.objectContaining({ operation: 'failure', cacheBytes: 0 })
        );
        expect(workers[0].terminate).toHaveBeenCalled();
        provider.dispose();
    });

    it('external cancellation rejects the request and permits retry', async () => {
        const task = setup();
        await task.provider.open();
        task.hold();
        const controller = new AbortController();
        const pending = task.provider.loadFrame(locator, controller.signal);
        const rejected = expect(pending).rejects.toMatchObject({ name: 'AbortError' });
        await vi.waitFor(() => expect(task.commands.at(-1)?.command.kind).toBe('frame'));
        controller.abort();
        await rejected;
        task.release();
        expect((await task.provider.loadFrame(locator)).positions.length).toBe(3);
        task.provider.dispose();
    });
});
