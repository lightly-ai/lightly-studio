import { describe, expect, it, vi } from 'vitest';
import type { CameraProjectionView } from '$lib/api/lightly_studio_local/types.gen';
import type { PointBatch } from '$lib/components/PointCloudViewer/types';
import { createCameraRgbColorComputer, type CameraPair } from './createCameraRgbColorComputer';

const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

function makeBatch(z: number): PointBatch {
    return { positions: new Float32Array([0, 0, z]), intensities: new Float32Array([0]), count: 1 };
}

function makePair(): CameraPair {
    const projection = {
        width: 4,
        height: 4,
        camera_matrix: new Array(9).fill(0),
        scene_to_camera: new Array(16).fill(0)
    } as unknown as CameraProjectionView;
    return { projection, blob: {} as Blob };
}

function makeMockWorker() {
    const posted: { id: number; cameras: { blob: Blob }[] }[] = [];
    const worker = {
        onmessage: null as ((event: MessageEvent) => void) | null,
        onerror: null as ((event: ErrorEvent) => void) | null,
        onmessageerror: null as ((event: MessageEvent) => void) | null,
        postMessage: (message: { id: number; cameras: { blob: Blob }[] }) => posted.push(message),
        terminate: vi.fn()
    };
    return {
        worker: worker as unknown as Worker,
        posted,
        respond(id: number, colors: Float32Array) {
            worker.onmessage?.({ data: { id, colors } } as MessageEvent);
        },
        respondWithError(id: number) {
            worker.onmessage?.({ data: { id, error: 'corrupt image' } } as MessageEvent);
        },
        cancel(id: number) {
            worker.onmessage?.({ data: { id, cancelled: true } } as MessageEvent);
        },
        fail() {
            worker.onerror?.({} as ErrorEvent);
        },
        get terminate() {
            return worker.terminate;
        }
    };
}

function setup() {
    const onColors = vi.fn<(colors: Float32Array | null) => void>();
    const mock = makeMockWorker();
    const computer = createCameraRgbColorComputer({
        onColors,
        createWorker: () => mock.worker
    });
    return { onColors, computer, mock };
}

describe('createCameraRgbColorComputer', () => {
    it('clears to neutral without a batch or cameras', () => {
        const { onColors, computer } = setup();
        computer.request(undefined, [makePair()]);
        computer.request(makeBatch(1), []);
        expect(onColors).toHaveBeenNthCalledWith(1, null);
        expect(onColors).toHaveBeenNthCalledWith(2, null);
    });

    it('stops in-flight camera work when camera colors are disabled', () => {
        const { onColors, computer, mock } = setup();
        const batch = makeBatch(1);
        const pair = makePair();
        computer.request(batch, [pair]);
        const requestId = mock.posted[0].id;

        computer.request(undefined, []);
        expect(mock.terminate).toHaveBeenCalledOnce();
        mock.respond(requestId, new Float32Array([1, 0, 0]));
        expect(onColors).toHaveBeenLastCalledWith(null);

        computer.request(batch, [pair]);
        expect(mock.posted).toHaveLength(2);
    });

    it('sends encoded images to the worker and applies its result for the current batch', () => {
        const { onColors, computer, mock } = setup();
        const batch = makeBatch(1);
        const pair = makePair();
        computer.request(batch, [pair]);
        expect(onColors).toHaveBeenLastCalledWith(null);
        expect(mock.posted).toHaveLength(1);
        expect(mock.posted[0].cameras[0].blob).toBe(pair.blob);

        const colors = new Float32Array([1, 0, 0]);
        mock.respond(mock.posted[0].id, colors);
        expect(onColors).toHaveBeenLastCalledWith(colors);
    });

    it('ignores a result for a batch that is no longer current', () => {
        const { computer, mock } = setup();
        const stale = makeBatch(1);
        const current = makeBatch(2);
        computer.request(stale, [makePair()]);
        computer.request(current, [makePair()]);
        expect(mock.posted).toHaveLength(2);
    });

    it('ignores a stale worker result and reuses cached colors when the batch returns', async () => {
        const { onColors, computer, mock } = setup();
        const first = makeBatch(1);
        const second = makeBatch(2);
        const pair = makePair();

        computer.request(first, [pair]);
        await flush();
        computer.request(second, [pair]);
        await flush();
        expect(mock.posted).toHaveLength(2);

        const firstColors = new Float32Array([1, 0, 0]);
        const secondColors = new Float32Array([0, 0, 1]);
        mock.respond(mock.posted[0].id, firstColors); // first is no longer current
        expect(onColors).not.toHaveBeenLastCalledWith(firstColors);
        mock.respond(mock.posted[1].id, secondColors);
        expect(onColors).toHaveBeenLastCalledWith(secondColors);

        // Returning to the first batch reuses its cached colors without recomputing.
        onColors.mockClear();
        computer.request(first, [pair]);
        expect(onColors).toHaveBeenCalledWith(firstColors);
        await flush();
        expect(mock.posted).toHaveLength(2);
    });

    it('evicts old point colors when more batches are visited', () => {
        const { computer, mock } = setup();
        const pair = makePair();
        const first = makeBatch(1);
        const second = makeBatch(2);
        const third = makeBatch(3);
        for (const batch of [first, second, third]) {
            computer.request(batch, [pair]);
            mock.respond(mock.posted.at(-1)!.id, new Float32Array([1, 0, 0]));
        }

        computer.request(second, [pair]);
        expect(mock.posted).toHaveLength(3);
        computer.request(first, [pair]);
        expect(mock.posted).toHaveLength(4);
    });

    it('does not duplicate work for the same batch already in flight', async () => {
        const { computer, mock } = setup();
        const batch = makeBatch(1);
        const pair = makePair();
        computer.request(batch, [pair]);
        computer.request(batch, [pair]);
        await flush();
        expect(mock.posted).toHaveLength(1);
    });

    it('retries a batch whose queued worker request was cancelled', () => {
        const { computer, mock } = setup();
        const batch = makeBatch(1);
        const pair = makePair();
        computer.request(batch, [pair]);
        mock.cancel(mock.posted[0].id);
        computer.request(batch, [pair]);
        expect(mock.posted).toHaveLength(2);
    });

    it('ignores a worker result whose cameras are no longer current for the same batch', async () => {
        const { onColors, computer, mock } = setup();
        const batch = makeBatch(1);

        computer.request(batch, [makePair()]);
        await flush();
        // Same batch, different cameras: a new signature supersedes the in-flight request.
        computer.request(batch, [makePair()]);
        await flush();
        expect(mock.posted).toHaveLength(2);

        const staleColors = new Float32Array([1, 0, 0]);
        const freshColors = new Float32Array([0, 0, 1]);
        mock.respond(mock.posted[0].id, staleColors);
        expect(onColors).not.toHaveBeenLastCalledWith(staleColors);
        mock.respond(mock.posted[1].id, freshColors);
        expect(onColors).toHaveBeenLastCalledWith(freshColors);
    });

    it('recomputes a batch after a worker decode failure instead of stranding it', () => {
        const { onColors, computer, mock } = setup();
        const batch = makeBatch(1);
        const pair = makePair();
        const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined);

        computer.request(batch, [pair]);
        mock.respondWithError(mock.posted[0].id);
        expect(onColors).toHaveBeenLastCalledWith(null);

        // The failed request must not dedupe later attempts for the same batch.
        computer.request(batch, [pair]);
        expect(mock.posted).toHaveLength(2);
        consoleError.mockRestore();
    });

    it('replaces the worker and clears pending after a worker failure', async () => {
        const { onColors, computer, mock } = setup();
        const first = makeBatch(1);
        const second = makeBatch(2);

        computer.request(first, [makePair()]);
        await flush();
        expect(mock.posted).toHaveLength(1);

        mock.fail();
        expect(mock.terminate).toHaveBeenCalledOnce();
        expect(onColors).toHaveBeenLastCalledWith(null);

        // A fresh worker keeps serving requests; the stranded one did not block the queue.
        computer.request(second, [makePair()]);
        await flush();
        expect(mock.posted).toHaveLength(2);
    });

    it('terminates the worker on dispose', () => {
        const { computer, mock } = setup();
        computer.request(makeBatch(1), [makePair()]);
        computer.dispose();
        expect(mock.terminate).toHaveBeenCalledOnce();
    });
});
