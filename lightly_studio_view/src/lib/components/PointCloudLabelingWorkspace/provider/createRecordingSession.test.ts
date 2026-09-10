import { describe, expect, it, vi, type Mock } from 'vitest';
import { canonicalCoordinateFrame } from '../domain';
import { createRecordingSession } from './createRecordingSession';
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
const metadata = { topics: [], firstLogTimeNs: '100', lastLogTimeNs: '200' };

interface FakeWorker {
    onmessage: ((event: MessageEvent<WorkerResult>) => void) | null;
    onerror: ((event: ErrorEvent) => void) | null;
    terminate: Mock<() => void>;
    postMessage: (message: WorkerRequest) => void;
}

function setup() {
    const commands: WorkerRequest[] = [];
    const held: (() => void)[] = [];
    let hold = false;
    const worker: FakeWorker = {
        onmessage: null,
        onerror: null,
        terminate: vi.fn(),
        postMessage: (message) => {
            commands.push(message);
            const reply = () => {
                const result: WorkerResult = { requestId: message.requestId, durationMs: 1 };
                if (message.command.kind === 'open') result.metadata = metadata;
                if (message.command.kind === 'range')
                    result.range = { frames: [locator], truncated: false };
                if (message.command.kind === 'frame')
                    result.frame = {
                        id: 'frame-1',
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
            };
            if (hold && message.command.kind !== 'open') held.push(reply);
            else queueMicrotask(reply);
        }
    };
    const onTelemetry = vi.fn();
    const onProgress = vi.fn();
    return {
        commands,
        worker,
        onTelemetry,
        onProgress,
        open: () =>
            createRecordingSession({
                source,
                createWorker: () => worker,
                onProgress,
                onTelemetry
            }),
        hold: () => {
            hold = true;
        },
        release: () => {
            hold = false;
            held.splice(0).forEach((reply) => reply());
        }
    };
}

describe('createRecordingSession', () => {
    it('opens the recording once and exposes its metadata', async () => {
        const task = setup();

        const session = await task.open();

        expect(session.metadata).toEqual(metadata);
        expect(session.source).toEqual(source);
        expect(task.commands.map((request) => request.command.kind)).toEqual(['open']);
        expect(task.onTelemetry).toHaveBeenCalledWith(
            expect.objectContaining({ operation: 'open' })
        );
    });

    it('reads a frame at the requested point budget', async () => {
        const task = setup();
        const session = await task.open();

        const frame = await session.readFrame(locator, { pointBudget: 1000 });

        expect(frame.positions.copy()).toEqual(new Float32Array([1, 2, 3]));
        expect(task.commands.at(-1)?.command).toMatchObject({ kind: 'frame', pointBudget: 1000 });
        expect(task.onTelemetry).toHaveBeenCalledWith(
            expect.objectContaining({ operation: 'decode' })
        );
    });

    it('posts commands that survive being cloned into the worker', async () => {
        const task = setup();
        const session = await task.open();
        // Callers hold locators in whatever they like — a Svelte deep state proxy, here —
        // and a proxy cannot be structured-cloned.
        const proxied = new Proxy({ ...locator }, {});

        await session.readFrame(proxied);
        await session.listFrames(
            new Proxy({ channelId: 1, startTimeNs: '1', endTimeNs: '2', limit: 5 }, {})
        );

        for (const request of task.commands) {
            expect(() => structuredClone(request)).not.toThrow();
        }
        expect(task.commands.at(-2)?.command).toEqual({
            kind: 'frame',
            locator: { channelId: 1, logTimeNs: '100', occurrence: 0 },
            pointBudget: 350_000
        });
    });

    it('lists frame locators for a window', async () => {
        const task = setup();
        const session = await task.open();

        expect(
            await session.listFrames({ channelId: 1, startTimeNs: '1', endTimeNs: '2', limit: 5 })
        ).toEqual([locator]);
        expect(task.commands.at(-1)?.command).toMatchObject({ kind: 'range', limit: 5 });
    });

    it('queues concurrent reads instead of pre-empting them', async () => {
        const task = setup();
        const session = await task.open();
        task.hold();

        const first = session.readFrame(locator);
        const second = session.readFrame({ ...locator, occurrence: 1 });
        // Only the first command reached the worker; the second waits its turn.
        await vi.waitFor(() =>
            expect(
                task.commands.filter((request) => request.command.kind === 'frame')
            ).toHaveLength(1)
        );

        task.release();
        await first;
        await vi.waitFor(() =>
            expect(
                task.commands.filter((request) => request.command.kind === 'frame')
            ).toHaveLength(2)
        );
        task.release();
        await second;
        expect(task.worker.terminate).not.toHaveBeenCalled();
    });

    it('abandons a queued read without disturbing the worker', async () => {
        const task = setup();
        const session = await task.open();
        task.hold();
        const controller = new AbortController();

        const visible = session.readFrame(locator);
        const abandoned = session.readFrame({ ...locator, occurrence: 1 }, {}, controller.signal);
        controller.abort();

        // Rejects at once rather than waiting for a turn it will never take.
        await expect(abandoned).rejects.toMatchObject({ name: 'AbortError' });
        task.release();
        await visible;
        // The abandoned read never reached the worker, so the parsed index survived.
        expect(task.commands.filter((request) => request.command.kind === 'frame')).toHaveLength(1);
        expect(task.worker.terminate).not.toHaveBeenCalled();
    });

    it('reports worker failures with their code', async () => {
        const task = setup();
        const session = await task.open();
        task.worker.postMessage = (message) => {
            queueMicrotask(() =>
                task.worker.onmessage?.({
                    data: {
                        requestId: message.requestId,
                        error: { code: 'schema', message: 'Unsupported channel.' }
                    }
                } as MessageEvent<WorkerResult>)
            );
        };

        await expect(session.readFrame(locator)).rejects.toMatchObject({
            name: 'ProviderError',
            code: 'schema'
        });
    });

    it('releases the worker when disposed, and when opening fails', async () => {
        const task = setup();
        const session = await task.open();

        session.dispose();
        expect(task.worker.terminate).toHaveBeenCalled();

        const failing = setup();
        failing.worker.postMessage = () => {
            throw new Error('worker is gone');
        };
        await expect(failing.open()).rejects.toThrow(/worker is gone/);
        expect(failing.worker.terminate).toHaveBeenCalled();
    });
});
