import type { PointBatch } from './pointCloudBuffer';

/**
 * Generate points on the 6 faces of a solid cube centered at the given offset.
 */
export function generateCube(
    size: number,
    count: number,
    offsetX = 0,
    offsetY = 0,
    offsetZ = 0
): PointBatch {
    const positions = new Float32Array(count * 3);
    const intensities = new Float32Array(count);
    const half = size / 2;
    const perFace = Math.floor(count / 6);

    for (let i = 0; i < count; i++) {
        const face = Math.min(Math.floor(i / perFace), 5);
        const u = Math.random() * size - half;
        const v = Math.random() * size - half;
        let x: number, y: number, z: number;
        switch (face) {
            case 0:
                x = u;
                y = v;
                z = -half;
                break; // front
            case 1:
                x = u;
                y = v;
                z = half;
                break; // back
            case 2:
                x = -half;
                y = u;
                z = v;
                break; // left
            case 3:
                x = half;
                y = u;
                z = v;
                break; // right
            case 4:
                x = u;
                y = -half;
                z = v;
                break; // bottom
            default:
                x = u;
                y = half;
                z = v;
                break; // top
        }
        positions[i * 3] = x + offsetX;
        positions[i * 3 + 1] = y + offsetY;
        positions[i * 3 + 2] = z + offsetZ;
        const dist = Math.sqrt(x * x + y * y + z * z);
        intensities[i] = (dist / (half * Math.sqrt(3))) * 200 + Math.random() * 10;
    }
    return { positions, intensities, count };
}
