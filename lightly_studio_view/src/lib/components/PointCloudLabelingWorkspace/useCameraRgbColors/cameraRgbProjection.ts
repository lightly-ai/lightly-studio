/** Neutral gray for points no camera can see. Matches the point cloud's fallback color. */
export const NEUTRAL_GRAY = 0.5;

/** Points nearer than this (in camera space) are treated as behind the camera. */
const NEAR_PLANE = 1e-6;

/** One camera's decoded image data and projection matrices. */
export interface CameraData {
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

/**
 * Projects a scene point into a camera. On success writes `[screenX, screenY, depth]` into
 * `out` and returns `true`; returns `false` when the point is behind the camera or outside
 * the image. `out` is reused across calls so the hot loop allocates nothing.
 */
export function projectPoint(
    px: number,
    py: number,
    pz: number,
    camera: CameraData,
    out: Float64Array
): boolean {
    const m = camera.sceneToCamera;
    const cx = m[0] * px + m[1] * py + m[2] * pz + m[3];
    const cy = m[4] * px + m[5] * py + m[6] * pz + m[7];
    const cz = m[8] * px + m[9] * py + m[10] * pz + m[11];

    if (cz < NEAR_PLANE) return false;

    const k = camera.cameraMatrix;
    const screenX = (k[0] * cx + k[1] * cy + k[2] * cz) / cz;
    const screenY = (k[3] * cx + k[4] * cy + k[5] * cz) / cz;

    if (screenX < 0 || screenX > camera.projWidth || screenY < 0 || screenY > camera.projHeight) {
        return false;
    }

    out[0] = screenX;
    out[1] = screenY;
    out[2] = cz;
    return true;
}

/**
 * Samples the camera image at a projected coordinate and writes linear RGB into `colors`
 * at `offset`. Projected coordinates are in full resolution (projWidth × projHeight); the
 * decoded image is downscaled, so coordinates are scaled into image pixels before sampling.
 */
export function samplePixel(
    camera: CameraData,
    screenX: number,
    screenY: number,
    colors: Float32Array,
    offset: number
): void {
    const scaleX = camera.width / camera.projWidth;
    const scaleY = camera.height / camera.projHeight;
    const x = Math.min(Math.floor(screenX * scaleX), camera.width - 1);
    const y = Math.min(Math.floor(screenY * scaleY), camera.height - 1);
    const idx = (y * camera.width + x) * 4;
    colors[offset] = camera.pixels[idx] / 255;
    colors[offset + 1] = camera.pixels[idx + 1] / 255;
    colors[offset + 2] = camera.pixels[idx + 2] / 255;
}

/**
 * Back-projects each point into every camera and colors it from the closest-depth camera that
 * can see it. Points no camera sees stay {@link NEUTRAL_GRAY}. Returns packed linear RGB
 * `[r0,g0,b0, ...]` of length `count * 3`.
 */
export function computeCameraRgbColors(
    positions: Float32Array,
    count: number,
    cameras: readonly CameraData[]
): Float32Array {
    const colors = new Float32Array(count * 3).fill(NEUTRAL_GRAY);
    const projected = new Float64Array(3);

    for (let i = 0; i < count; i++) {
        const offset = i * 3;
        const px = positions[offset];
        const py = positions[offset + 1];
        const pz = positions[offset + 2];

        let bestDepth = Infinity;
        for (const camera of cameras) {
            if (!projectPoint(px, py, pz, camera, projected)) continue;
            if (projected[2] >= bestDepth) continue;
            // A strictly closer camera overwrites the previous color written at this offset,
            // so after the loop the offset holds the nearest camera's sample.
            bestDepth = projected[2];
            samplePixel(camera, projected[0], projected[1], colors, offset);
        }
    }

    return colors;
}
