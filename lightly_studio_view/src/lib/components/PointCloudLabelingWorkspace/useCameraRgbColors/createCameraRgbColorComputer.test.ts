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
    const posted: { id: number }[] = [];
    const worker = {
        onmessage: null as ((event: MessageEvent) => void) | null,
        onerror: null as ((event: ErrorEvent) => void) | null,
        onmessageerror: null as ((event: MessageEvent) => void) | null,
        postMessage: (message: { id: number }) => posted.push(message),
        terminate: vi.fn()
    };
    return {
        worker: worker as unknown as Worker,
        posted,
        respond(id: number, colors: Float32Array) {
            worker.onmessage?.({ data: { id, colors } } as MessageEvent);
        },
        fail() {
            worker.onerror?.({} as ErrorEvent);
        },
        get terminate() {
            return worker.terminate;
        }
    };
}

const decode = async (): Promise<ImageData> =>
    ({ width: 2, height: 2, data: new Uint8ClampedArray(16) }) as ImageData;

function setup(decodeOverride: (blob: Blob) => Promise<ImageData> = decode) {
    const onColors = vi.fn<(colors: Float32Array | null) => void>();
    const mock = makeMockWorker();
    const computer = createCameraRgbColorComputer({
        onColors,
        createWorker: () => mock.worker,
        decode: decodeOverride
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

    it('shows the neutral fallback, then applies the worker result for the current batch', async () => {
        const { onColors, computer, mock } = setup();
        const batch = makeBatch(1);
        computer.request(batch, [makePair()]);
        expect(onColors).toHaveBeenLastCalledWith(null);

        await flush();
        expect(mock.posted).toHaveLength(1);

        const colors = new Float32Array([1, 0, 0]);
        mock.respond(mock.posted[0].id, colors);
        expect(onColors).toHaveBeenLastCalledWith(colors);
    });

    it('drops a request whose batch is no longer current before it reaches the worker', async () => {
        const { computer, mock } = setup();
        const stale = makeBatch(1);
        const current = makeBatch(2);
        computer.request(stale, [makePair()]);
        computer.request(current, [makePair()]);

        await flush();
        expect(mock.posted).toHaveLength(1); // only the current batch is sent
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

    it('does not duplicate work for the same batch already in flight', async () => {
        const { computer, mock } = setup();
        const batch = makeBatch(1);
        const pair = makePair();
        computer.request(batch, [pair]);
        computer.request(batch, [pair]);
        await flush();
        expect(mock.posted).toHaveLength(1);
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

    it('recomputes a batch after a decode failure instead of stranding it', async () => {
        let failNext = true;
        const flakyDecode = async (): Promise<ImageData> => {
            if (failNext) throw new Error('corrupt image');
            return { width: 2, height: 2, data: new Uint8ClampedArray(16) } as ImageData;
        };
        const { onColors, computer, mock } = setup(flakyDecode);
        const batch = makeBatch(1);
        const pair = makePair();

        computer.request(batch, [pair]);
        await flush();
        expect(mock.posted).toHaveLength(0); // decode failed, nothing reached the worker
        expect(onColors).toHaveBeenLastCalledWith(null);

        // The failed request must not dedupe later attempts for the same batch.
        failNext = false;
        computer.request(batch, [pair]);
        await flush();
        expect(mock.posted).toHaveLength(1);
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
        computer.dispose();
        expect(mock.terminate).toHaveBeenCalledOnce();
    });
});
