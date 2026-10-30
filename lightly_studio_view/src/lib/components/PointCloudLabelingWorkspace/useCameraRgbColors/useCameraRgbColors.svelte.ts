import type { CameraProjectionView } from '$lib/api/lightly_studio_local/types.gen';
import type { ColorMode } from '$lib/components/PointCloudViewer';
import type { PointBatch } from '$lib/components/PointCloudViewer/types';

export interface CameraPair {
    projection: CameraProjectionView;
    blob: Blob;
}

interface UseCameraRgbColorsParams {
    getBatch: () => PointBatch | undefined;
    getColorMode: () => ColorMode;
    getCameraPairs: () => CameraPair[];
}

/** Cache decoded ImageData by Blob identity to avoid re-decoding on each render. */
const imageDataCache = new WeakMap<Blob, ImageData>();

async function decodeBlob(blob: Blob): Promise<ImageData> {
    const cached = imageDataCache.get(blob);
    if (cached) return cached;

    const bitmap = await createImageBitmap(blob);
    const canvas = new OffscreenCanvas(bitmap.width, bitmap.height);
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Failed to get OffscreenCanvas 2D context');
    ctx.drawImage(bitmap, 0, 0);
    bitmap.close();
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    imageDataCache.set(blob, imageData);
    return imageData;
}

/** Stable per-Blob ids so a batch's cached colors can be matched to the camera images used. */
const blobIds = new WeakMap<Blob, number>();
let nextBlobId = 1;

function cameraSignature(pairs: readonly CameraPair[]): string {
    return pairs
        .map(({ blob }) => {
            let id = blobIds.get(blob);
            if (id === undefined) {
                id = nextBlobId++;
                blobIds.set(blob, id);
            }
            return id;
        })
        .join('|');
}

/**
 * Computes per-point RGB colors by back-projecting camera images onto the point cloud.
 * Only active when colorMode is 'camera-rgb'. Uses a Web Worker for off-main-thread computation.
 * For each point, picks the closest-depth camera that can see it.
 */
export function useCameraRgbColors(params: UseCameraRgbColorsParams) {
    let colors = $state<Float32Array | null>(null);

    // Colors are cached per point batch, so a worker result is always matched to the batch it
    // was computed for and never applied to whichever batch happens to be on screen when it
    // returns. Without this, playback advances faster than the async pipeline and every result
    // is for a stale batch, leaving the cloud on the neutral fallback (all gray).
    const cache = new WeakMap<PointBatch, { signature: string; colors: Float32Array }>();
    const pending = new Map<number, { batch: PointBatch; signature: string }>();
    let latestBatch: PointBatch | undefined;
    let nextRequestId = 1;

    const worker = new Worker(new URL('./cameraRgbWorker.ts', import.meta.url), {
        type: 'module'
    });

    worker.onmessage = (event: MessageEvent<{ id: number; colors: Float32Array }>) => {
        const request = pending.get(event.data.id);
        if (!request) return;
        pending.delete(event.data.id);
        cache.set(request.batch, { signature: request.signature, colors: event.data.colors });
        if (request.batch === latestBatch) colors = event.data.colors;
    };

    $effect(() => {
        const colorMode = params.getColorMode();
        const batch = params.getBatch();
        const cameraPairs = params.getCameraPairs();

        if (colorMode !== 'camera-rgb' || !batch || cameraPairs.length === 0) {
            latestBatch = undefined;
            colors = null;
            return;
        }

        latestBatch = batch;
        const signature = cameraSignature(cameraPairs);

        const cached = cache.get(batch);
        if (cached?.signature === signature) {
            colors = cached.colors;
            return;
        }

        // Already computing this exact batch; keep the current state instead of duplicating work.
        for (const request of pending.values()) {
            if (request.batch === batch && request.signature === signature) return;
        }

        // New batch: show the neutral fallback until its own colors are ready, rather than
        // mis-applying the previous batch's colors to a different set of points.
        colors = null;
        const requestId = nextRequestId++;
        pending.set(requestId, { batch, signature });

        void (async () => {
            const decodedCameras = await Promise.all(
                cameraPairs.map(async ({ projection, blob }) => {
                    const imageData = await decodeBlob(blob);
                    return {
                        sceneToCamera: new Float64Array(projection.scene_to_camera.slice(0, 12)),
                        cameraMatrix: new Float64Array(projection.camera_matrix),
                        projWidth: projection.width,
                        projHeight: projection.height,
                        width: imageData.width,
                        height: imageData.height,
                        pixels: imageData.data
                    };
                })
            );

            // Playback moved on while decoding; drop the request to keep the worker queue short.
            // The frame is recomputed if it becomes current again.
            if (latestBatch !== batch) {
                pending.delete(requestId);
                return;
            }

            const positionsCopy = batch.positions.slice(0, batch.count * 3);
            worker.postMessage(
                {
                    id: requestId,
                    positions: positionsCopy,
                    count: batch.count,
                    cameras: decodedCameras
                },
                [positionsCopy.buffer]
            );
        })();
    });

    $effect(() => {
        return () => worker.terminate();
    });

    return {
        get colors() {
            return colors;
        }
    };
}
