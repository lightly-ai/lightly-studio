/// <reference lib="webworker" />

import { computeCameraRgbColors, type CameraData } from './cameraRgbProjection';
import { decodeCameraImage } from './decodeCameraImage';

export interface CameraInput {
    sceneToCamera: Float64Array;
    cameraMatrix: Float64Array;
    projWidth: number;
    projHeight: number;
    blob: Blob;
}

interface WorkerInput {
    /** Request id echoed back so the caller can match the result to its batch. */
    id: number;
    /** Flat point positions [x0,y0,z0, x1,y1,z1, ...]. */
    positions: Float32Array;
    /** Number of active points. */
    count: number;
    cameras: CameraInput[];
}

interface WorkerOutput {
    /** Request id from the matching {@link WorkerInput}. */
    id: number;
    /** Packed linear RGB [r0,g0,b0, ...] in [0,1]. Length = count * 3. */
    colors?: Float32Array;
    error?: string;
    cancelled?: boolean;
}

let queued: WorkerInput | undefined;
let processing = false;

self.onmessage = (event: MessageEvent<WorkerInput>) => {
    if (queued) {
        const result: WorkerOutput = { id: queued.id, cancelled: true };
        (self as unknown as Worker).postMessage(result);
    }
    queued = event.data;
    if (!processing) return processQueue();
};

async function processQueue(): Promise<void> {
    processing = true;
    while (queued) {
        const { id, positions, count, cameras } = queued;
        queued = undefined;
        try {
            const decoded: CameraData[] = await Promise.all(cameras.map(decodeCamera));
            if (queued) {
                const result: WorkerOutput = { id, cancelled: true };
                (self as unknown as Worker).postMessage(result);
                continue;
            }
            const colors = computeCameraRgbColors(positions, count, decoded);
            const result: WorkerOutput = { id, colors };
            (self as unknown as Worker).postMessage(result, [colors.buffer]);
        } catch (error) {
            const result: WorkerOutput = { id, error: String(error) };
            (self as unknown as Worker).postMessage(result);
        }
    }
    processing = false;
}

async function decodeCamera(camera: CameraInput): Promise<CameraData> {
    const imageData = await decodeCameraImage(camera.blob);
    return {
        sceneToCamera: camera.sceneToCamera,
        cameraMatrix: camera.cameraMatrix,
        projWidth: camera.projWidth,
        projHeight: camera.projHeight,
        width: imageData.width,
        height: imageData.height,
        pixels: imageData.data
    };
}
