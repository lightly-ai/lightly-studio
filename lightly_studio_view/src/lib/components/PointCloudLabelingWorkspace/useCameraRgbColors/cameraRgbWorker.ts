/// <reference lib="webworker" />

import { computeCameraRgbColors, type CameraData } from './cameraRgbProjection';

interface WorkerInput {
    /** Request id echoed back so the caller can match the result to its batch. */
    id: number;
    /** Flat point positions [x0,y0,z0, x1,y1,z1, ...]. */
    positions: Float32Array;
    /** Number of active points. */
    count: number;
    cameras: CameraData[];
}

interface WorkerOutput {
    /** Request id from the matching {@link WorkerInput}. */
    id: number;
    /** Packed linear RGB [r0,g0,b0, ...] in [0,1]. Length = count * 3. */
    colors: Float32Array;
}

self.onmessage = (event: MessageEvent<WorkerInput>) => {
    const { id, positions, count, cameras } = event.data;
    const colors = computeCameraRgbColors(positions, count, cameras);
    const result: WorkerOutput = { id, colors };
    (self as unknown as Worker).postMessage(result, [colors.buffer]);
};
