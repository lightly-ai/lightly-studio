import { describe, expect, it } from 'vitest';
import {
    NEUTRAL_GRAY,
    computeCameraRgbColors,
    projectPoint,
    samplePixel,
    type CameraData
} from './cameraRgbProjection';

/**
 * Builds a camera with an identity pose and a pinhole intrinsic (fx = fy = 1, principal point at
 * the image center), so a point at (0, 0, z) projects to the image center at depth z.
 */
function makeCamera(overrides: Partial<CameraData> = {}): CameraData {
    const projWidth = overrides.projWidth ?? 4;
    const projHeight = overrides.projHeight ?? 4;
    const width = overrides.width ?? projWidth;
    const height = overrides.height ?? projHeight;
    return {
        sceneToCamera: new Float64Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0]),
        cameraMatrix: new Float64Array([1, 0, projWidth / 2, 0, 1, projHeight / 2, 0, 0, 1]),
        projWidth,
        projHeight,
        width,
        height,
        pixels: overrides.pixels ?? new Uint8ClampedArray(width * height * 4),
        ...overrides
    };
}

describe('projectPoint', () => {
    it('projects an in-front point to the image center at its depth', () => {
        const out = new Float64Array(3);
        expect(projectPoint(0, 0, 1, makeCamera(), out)).toBe(true);
        expect(Array.from(out)).toEqual([2, 2, 1]);
    });

    it('rejects a point behind the camera', () => {
        const out = new Float64Array(3);
        expect(projectPoint(0, 0, -1, makeCamera(), out)).toBe(false);
        expect(projectPoint(0, 0, 0, makeCamera(), out)).toBe(false);
    });

    it('rejects a point that projects outside the image', () => {
        const out = new Float64Array(3);
        expect(projectPoint(10, 0, 1, makeCamera(), out)).toBe(false);
    });
});

describe('samplePixel', () => {
    it('scales full-resolution coordinates into a downscaled image before sampling', () => {
        // 2×2 image calibrated for a 4×4 projection: coordinates are halved before indexing.
        const pixels = new Uint8ClampedArray(2 * 2 * 4);
        const redIndex = (1 + 0 * 2) * 4; // pixel (x=1, y=0)
        pixels[redIndex] = 255;
        pixels[redIndex + 3] = 255;
        const camera = makeCamera({ projWidth: 4, projHeight: 4, width: 2, height: 2, pixels });

        const colors = new Float32Array(3);
        samplePixel(camera, 3, 1, colors, 0); // floor(3 * 0.5)=1, floor(1 * 0.5)=0
        expect(Array.from(colors)).toEqual([1, 0, 0]);
    });

    it('clamps coordinates on the far edge to the last pixel', () => {
        const pixels = new Uint8ClampedArray(2 * 2 * 4).fill(0);
        const lastIndex = (1 + 1 * 2) * 4; // pixel (x=1, y=1)
        pixels[lastIndex + 1] = 255; // green
        const camera = makeCamera({ projWidth: 2, projHeight: 2, width: 2, height: 2, pixels });

        const colors = new Float32Array(3);
        samplePixel(camera, 2, 2, colors, 0); // floor(2)=2 clamps to width-1=1
        expect(Array.from(colors)).toEqual([0, 1, 0]);
    });
});

describe('computeCameraRgbColors', () => {
    const redCamera = () => makeCamera({ pixels: fillPixels(4, 4, [255, 0, 0]) });
    // Shifted 2 units further along z, so it is the farther view of a centered point.
    const blueCamera = () =>
        makeCamera({
            sceneToCamera: new Float64Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 2]),
            pixels: fillPixels(4, 4, [0, 0, 255])
        });

    it('colors each point from the closest-depth camera, regardless of camera order', () => {
        const positions = new Float32Array([0, 0, 1]);
        const near = computeCameraRgbColors(positions, 1, [blueCamera(), redCamera()]);
        const flipped = computeCameraRgbColors(positions, 1, [redCamera(), blueCamera()]);
        // redCamera sees the point at depth 1, blueCamera at depth 3 → red wins both times.
        expect(Array.from(near)).toEqual([1, 0, 0]);
        expect(Array.from(flipped)).toEqual([1, 0, 0]);
    });

    it('leaves points no camera can see at the neutral fallback', () => {
        const positions = new Float32Array([0, 0, -5]);
        const colors = computeCameraRgbColors(positions, 1, [redCamera(), blueCamera()]);
        expect(Array.from(colors)).toEqual([NEUTRAL_GRAY, NEUTRAL_GRAY, NEUTRAL_GRAY]);
    });

    it('colors visible points and keeps invisible ones neutral within one batch', () => {
        const positions = new Float32Array([0, 0, 1, 0, 0, -5]);
        const colors = computeCameraRgbColors(positions, 2, [redCamera()]);
        expect(Array.from(colors)).toEqual([1, 0, 0, NEUTRAL_GRAY, NEUTRAL_GRAY, NEUTRAL_GRAY]);
    });
});

function fillPixels(width: number, height: number, [r, g, b]: [number, number, number]) {
    const pixels = new Uint8ClampedArray(width * height * 4);
    for (let i = 0; i < width * height; i++) {
        pixels[i * 4] = r;
        pixels[i * 4 + 1] = g;
        pixels[i * 4 + 2] = b;
        pixels[i * 4 + 3] = 255;
    }
    return pixels;
}
