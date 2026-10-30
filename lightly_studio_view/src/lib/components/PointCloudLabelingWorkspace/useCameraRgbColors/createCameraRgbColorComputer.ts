import type { CameraProjectionView } from '$lib/api/lightly_studio_local/types.gen';
import type { PointBatch } from '$lib/components/PointCloudViewer';
import type { CameraData } from './cameraRgbProjection';
import { decodeCameraImage } from './decodeCameraImage';

/** A camera's projection metadata paired with its (still encoded) image for one tick. */
export interface CameraPair {
    projection: CameraProjectionView;
    blob: Blob;
}

interface ComputerDeps {
    /** Called with the colors for the latest requested batch, or null for the neutral fallback. */
    onColors: (colors: Float32Array | null) => void;
    /** Overridable for tests; defaults to the bundled projection worker. */
    createWorker?: () => Worker;
    /** Overridable for tests; defaults to {@link decodeCameraImage}. */
    decode?: (blob: Blob) => Promise<ImageData>;
}

interface WorkerResult {
    id: number;
    colors: Float32Array;
}

/**
 * Owns the projection worker and matches each async result to the batch it was computed for.
 *
 * Colors are cached per point batch so a worker result is only applied to its own batch, never
 * to whichever batch happens to be on screen when it returns. Without this, playback advances
 * faster than the async pipeline and every result is for a stale batch, leaving the cloud on the
 * neutral fallback (all gray).
 */
export function createCameraRgbColorComputer(deps: ComputerDeps) {
    const { onColors } = deps;
    const decode = deps.decode ?? decodeCameraImage;
    const createWorker =
        deps.createWorker ??
        (() => new Worker(new URL('./cameraRgbWorker.ts', import.meta.url), { type: 'module' }));

    const cache = new WeakMap<PointBatch, { signature: string; colors: Float32Array }>();
    const pending = new Map<number, { batch: PointBatch; signature: string }>();
    const blobIds = new WeakMap<Blob, number>();
    let nextBlobId = 1;
    let latestBatch: PointBatch | undefined;
    let latestSignature: string | undefined;
    let nextRequestId = 1;

    let worker = startWorker();

    function startWorker(): Worker {
        const instance = createWorker();
        instance.onmessage = (event: MessageEvent<WorkerResult>) => {
            const request = pending.get(event.data.id);
            if (!request) return;
            pending.delete(event.data.id);
            cache.set(request.batch, { signature: request.signature, colors: event.data.colors });
            // Only apply to the on-screen batch if both it and its cameras are still current:
            // a newer request may have changed the cameras while this batch stayed displayed.
            if (request.batch === latestBatch && request.signature === latestSignature) {
                onColors(event.data.colors);
            }
        };
        // A worker crash would otherwise strand its in-flight requests in `pending`, so later
        // requests for the same batch dedupe against them and never recompute. Drop them and
        // replace the worker so the next request can run on a fresh instance.
        instance.onerror = recoverFromWorkerFailure;
        instance.onmessageerror = recoverFromWorkerFailure;
        return instance;
    }

    function recoverFromWorkerFailure(): void {
        pending.clear();
        worker.terminate();
        worker = startWorker();
        onColors(null);
    }

    // Stable per-blob ids plus the projection parameters let a batch's cached colors be matched to
    // the exact camera images and projection used, so a cache hit never reuses colors computed for
    // a different projection even when the same blob is reprojected.
    function cameraSignature(pairs: readonly CameraPair[]): string {
        return pairs
            .map(({ projection, blob }) => {
                let id = blobIds.get(blob);
                if (id === undefined) {
                    id = nextBlobId++;
                    blobIds.set(blob, id);
                }
                return JSON.stringify([
                    id,
                    projection.scene_to_camera,
                    projection.camera_matrix,
                    projection.width,
                    projection.height
                ]);
            })
            .join('|');
    }

    /** Requests colors for `batch`. Pass `undefined` batch (or no cameras) to clear to neutral. */
    function request(batch: PointBatch | undefined, cameraPairs: readonly CameraPair[]): void {
        if (!batch || cameraPairs.length === 0) {
            latestBatch = undefined;
            latestSignature = undefined;
            onColors(null);
            return;
        }

        latestBatch = batch;
        const signature = cameraSignature(cameraPairs);
        latestSignature = signature;

        const cached = cache.get(batch);
        if (cached?.signature === signature) {
            onColors(cached.colors);
            return;
        }

        // Already computing this exact batch; keep the current state instead of duplicating work.
        for (const inFlight of pending.values()) {
            if (inFlight.batch === batch && inFlight.signature === signature) return;
        }

        // New batch: show the neutral fallback until its own colors are ready, rather than
        // mis-applying the previous batch's colors to a different set of points.
        onColors(null);
        const requestId = nextRequestId++;
        pending.set(requestId, { batch, signature });

        void (async () => {
            let cameras: CameraData[];
            try {
                cameras = await Promise.all(
                    cameraPairs.map(({ projection, blob }) =>
                        toCameraData(projection, blob, decode)
                    )
                );
            } catch (error) {
                // A failed decode (e.g. a corrupt image) must not strand the request in `pending`,
                // or later requests for this batch would dedupe against it and never recompute.
                pending.delete(requestId);
                if (latestBatch === batch) onColors(null);
                console.error('Failed to decode camera images for RGB projection', error);
                return;
            }

            // Playback moved on while decoding; drop the request to keep the worker queue short.
            // The frame is recomputed if it becomes current again.
            if (latestBatch !== batch) {
                pending.delete(requestId);
                return;
            }

            const positions = batch.positions.slice(0, batch.count * 3);
            worker.postMessage({ id: requestId, positions, count: batch.count, cameras }, [
                positions.buffer
            ]);
        })();
    }

    return {
        request,
        dispose: () => worker.terminate()
    };
}

async function toCameraData(
    projection: CameraProjectionView,
    blob: Blob,
    decode: (blob: Blob) => Promise<ImageData>
): Promise<CameraData> {
    const imageData = await decode(blob);
    return {
        sceneToCamera: new Float64Array(projection.scene_to_camera.slice(0, 12)),
        cameraMatrix: new Float64Array(projection.camera_matrix),
        projWidth: projection.width,
        projHeight: projection.height,
        width: imageData.width,
        height: imageData.height,
        pixels: imageData.data
    };
}
