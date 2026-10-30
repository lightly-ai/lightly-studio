/** One camera's decoded image data and projection matrices. */
interface CameraData {
    /** Row-major 3×4 scene-to-camera transform (first 12 values of the 4×4 matrix). */
    sceneToCamera: Float64Array;
    /** Row-major 3×3 camera intrinsic matrix, calibrated for projWidth × projHeight. */
    cameraMatrix: Float64Array;
    /** Full sensor resolution the camera matrix is calibrated for. */
    projWidth: number;
    projHeight: number;
    /** Decoded image resolution (downscaled); may differ from projWidth/projHeight. */
    width: number;
    height: number;
    /** RGBA pixel data from ImageData.data. Length = width * height * 4. */
    pixels: Uint8ClampedArray;
}

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

const NEAR_PLANE = 1e-6;
const NEUTRAL = 0.5;

function projectPoint(
    px: number,
    py: number,
    pz: number,
    camera: CameraData
): { screenX: number; screenY: number; depth: number } | null {
    const m = camera.sceneToCamera;
    const cx = m[0] * px + m[1] * py + m[2] * pz + m[3];
    const cy = m[4] * px + m[5] * py + m[6] * pz + m[7];
    const cz = m[8] * px + m[9] * py + m[10] * pz + m[11];

    if (cz < NEAR_PLANE) return null;

    const k = camera.cameraMatrix;
    const screenX = (k[0] * cx + k[1] * cy + k[2] * cz) / cz;
    const screenY = (k[3] * cx + k[4] * cy + k[5] * cz) / cz;

    if (screenX < 0 || screenX > camera.projWidth || screenY < 0 || screenY > camera.projHeight) {
        return null;
    }

    return { screenX, screenY, depth: cz };
}

function samplePixel(
    camera: CameraData,
    screenX: number,
    screenY: number
): [number, number, number] {
    // Projected coordinates are in full-resolution (projWidth × projHeight); the decoded
    // image is downscaled, so scale into image pixels before sampling.
    const scaleX = camera.width / camera.projWidth;
    const scaleY = camera.height / camera.projHeight;
    const x = Math.min(Math.floor(screenX * scaleX), camera.width - 1);
    const y = Math.min(Math.floor(screenY * scaleY), camera.height - 1);
    const idx = (y * camera.width + x) * 4;
    return [camera.pixels[idx] / 255, camera.pixels[idx + 1] / 255, camera.pixels[idx + 2] / 255];
}

function computeColors(input: WorkerInput): Float32Array {
    const { positions, count, cameras } = input;
    const colors = new Float32Array(count * 3).fill(NEUTRAL);

    for (let i = 0; i < count; i++) {
        const offset = i * 3;
        const px = positions[offset];
        const py = positions[offset + 1];
        const pz = positions[offset + 2];

        let bestDepth = Infinity;
        let bestColor: [number, number, number] | null = null;

        for (const camera of cameras) {
            const projected = projectPoint(px, py, pz, camera);
            if (!projected || projected.depth >= bestDepth) continue;
            bestDepth = projected.depth;
            bestColor = samplePixel(camera, projected.screenX, projected.screenY);
        }

        if (bestColor) {
            colors[offset] = bestColor[0];
            colors[offset + 1] = bestColor[1];
            colors[offset + 2] = bestColor[2];
        }
    }

    return colors;
}

self.onmessage = (event: MessageEvent<WorkerInput>) => {
    const colors = computeColors(event.data);
    const result: WorkerOutput = { id: event.data.id, colors };
    (self as unknown as Worker).postMessage(result, [colors.buffer]);
};
