import { afterEach, describe, expect, it, vi } from 'vitest';
import { canonicalCoordinateFrame } from '../domain';
import type { WorkerCommand, WorkerResult } from './workerProtocol';

const { openMcap } = vi.hoisted(() => ({ openMcap: vi.fn() }));
vi.mock('./mcapReader', () => ({ openMcap }));

const source = {
    recordingId: 'r',
    version: 'v',
    url: '/recording',
    sizeBytes: '100',
    coordinateFrame: canonicalCoordinateFrame('lidar'),
    logClockId: 'log',
    publishClockId: 'pub'
};

function frame() {
    return {
        id: 'f',
        source: { recordingId: 'r', streamId: '1', messageId: 'm', publishedAt: null },
        timestamp: { nanoseconds: '100', clockId: 'log' },
        coordinateFrame: source.coordinateFrame,
        sourcePointCount: 1,
        positions: new Float32Array([1, 2, 3]),
        cameras: []
    };
}

function session() {
    return {
        metadata: { topics: [], firstLogTimeNs: '1', lastLogTimeNs: '2' },
        loadFrame: vi.fn(async () => frame()),
        listFrames: vi.fn(async () => ({ frames: [], truncated: false })),
        readable: { bytesRead: 0 }
    };
}

/** Loads a fresh worker module so its recording session starts unopened. */
async function loadWorker() {
    const posted: { message: WorkerResult; transfer?: readonly ArrayBuffer[] }[] = [];
    const scope = {
        onmessage: null as ((event: MessageEvent) => Promise<void>) | null,
        postMessage: (message: WorkerResult, options?: { transfer: ArrayBuffer[] }) =>
            posted.push({ message, transfer: options?.transfer })
    };
    vi.stubGlobal('self', scope);
    vi.resetModules();
    await import('./mcap.worker');
    // The worker's own module graph is reloaded, so its error class is too.
    const { ProviderError } = await import('./providerError');
    return {
        posted,
        ProviderError,
        send: (command: WorkerCommand, requestId = 1) =>
            scope.onmessage!({ data: { requestId, command } } as MessageEvent)
    };
}

afterEach(() => {
    vi.unstubAllGlobals();
    openMcap.mockReset();
});

describe('mcap.worker', () => {
    it('reports phases, returns metadata, and transfers decoded frame buffers', async () => {
        const active = session();
        openMcap.mockResolvedValue(active);
        const { posted, send } = await loadWorker();

        await send({ kind: 'open', source });
        expect(posted[0].message).toMatchObject({ requestId: 1, phase: 'indexing' });
        expect(posted[1].message.metadata).toEqual(active.metadata);

        active.loadFrame.mockImplementation(async () => {
            active.readable.bytesRead += 48;
            return frame();
        });
        await send(
            {
                kind: 'frame',
                locator: { channelId: 1, logTimeNs: '100', occurrence: 0 },
                pointBudget: 10
            },
            2
        );
        expect(posted[2].message).toMatchObject({ requestId: 2, phase: 'decoding' });
        expect(posted[3].message.frame?.positions).toEqual(new Float32Array([1, 2, 3]));
        expect(posted[3].message.bytesRead).toBe(48);
        expect(posted[3].transfer).toEqual([posted[3].message.frame?.positions.buffer]);

        await send({ kind: 'range', channelId: 1, startTimeNs: '1', endTimeNs: '2', limit: 5 }, 3);
        expect(active.listFrames).toHaveBeenCalledWith(1, '1', '2', 5);
        expect(posted[5].message.range).toEqual({ frames: [], truncated: false });
    });

    it('requires an open recording before frame and range requests', async () => {
        const { posted, send } = await loadWorker();
        await send({ kind: 'range', channelId: 1, startTimeNs: '1', endTimeNs: '2', limit: 5 });
        expect(posted[1].message.error).toEqual({
            code: 'source',
            message: 'Open a recording before requesting frames.'
        });
        expect(posted[1].message.durationMs).toBeGreaterThanOrEqual(0);
    });

    it('forwards provider error codes and hides unexpected failures', async () => {
        const active = session();
        openMcap.mockResolvedValue(active);
        const { posted, send, ProviderError } = await loadWorker();
        await send({ kind: 'open', source });

        active.loadFrame.mockRejectedValueOnce(new ProviderError('fields', 'Missing intensity.'));
        const locator = { channelId: 1, logTimeNs: '100', occurrence: 0 };
        await send({ kind: 'frame', locator, pointBudget: 10 }, 2);
        expect(posted[3].message.error).toEqual({ code: 'fields', message: 'Missing intensity.' });

        active.loadFrame.mockRejectedValueOnce(new RangeError('offset is out of bounds'));
        await send({ kind: 'frame', locator, pointBudget: 10 }, 3);
        expect(posted[5].message.error?.code).toBe('corrupt');
        expect(posted[5].message.error?.message).not.toMatch(/offset/);
        // The cause is not shown to users, but it must still be recoverable for logs.
        expect(posted[5].message.error?.detail).toBe('RangeError: offset is out of bounds');
    });

    it('reports a failure to index the recording', async () => {
        const { posted, send, ProviderError } = await loadWorker();
        openMcap.mockRejectedValue(new ProviderError('auth', 'Recording access was denied.'));
        await send({ kind: 'open', source });
        expect(posted[1].message.error).toEqual({
            code: 'auth',
            message: 'Recording access was denied.'
        });
    });
});
