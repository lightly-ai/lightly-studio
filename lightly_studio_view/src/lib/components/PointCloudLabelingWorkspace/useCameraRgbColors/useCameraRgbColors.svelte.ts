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

/**
 * Computes per-point RGB colors by back-projecting camera images onto the point cloud.
 * Only active when colorMode is 'camera-rgb'. Uses a Web Worker for off-main-thread computation.
 * For each point, picks the closest-depth camera that can see it.
 */
export function useCameraRgbColors(params: UseCameraRgbColorsParams) {
    let colors = $state<Float32Array | null>(null);
    let requestId = 0;

    const worker = new Worker(new URL('./cameraRgbWorker.ts', import.meta.url), {
        type: 'module'
    });

    $effect(() => {
        const colorMode = params.getColorMode();
        const batch = params.getBatch();
        const cameraPairs = params.getCameraPairs();

        console.warn('[rgb] hook effect', {
            colorMode,
            batchCount: batch?.count,
            cameraPairs: cameraPairs.length
        });

        if (colorMode !== 'camera-rgb' || !batch || cameraPairs.length === 0) {
            colors = null;
            return;
        }

        const currentId = ++requestId;

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

            if (currentId !== requestId) return;

            const positionsCopy = batch.positions.slice(0, batch.count * 3);

            worker.onmessage = (event: MessageEvent<{ colors: Float32Array }>) => {
                if (currentId !== requestId) return;
                const c = event.data.colors;
                let colored = 0;
                for (let i = 0; i < c.length; i += 3) {
                    if (c[i] !== 0.5 || c[i + 1] !== 0.5 || c[i + 2] !== 0.5) colored++;
                }
                console.warn('[rgb] worker result', {
                    length: c.length,
                    coloredPoints: colored,
                    sample: [c[0], c[1], c[2]]
                });
                colors = c;
            };

            worker.postMessage(
                { positions: positionsCopy, count: batch.count, cameras: decodedCameras },
                [positionsCopy.buffer]
            );
        })();

        return () => {
            requestId++;
        };
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
