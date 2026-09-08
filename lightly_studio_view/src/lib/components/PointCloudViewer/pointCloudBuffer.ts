import { Box3, BufferAttribute, BufferGeometry, Sphere } from 'three';
import { buildColorBuffer, computeActiveBounds } from './pointCloudUtils';
import type { ColorMode } from './pointCloudUtils';

/** A batch of points stored in pre-packed typed arrays. */
export interface PointBatch {
    /** Flat position data [x0,y0,z0, x1,y1,z1, ...]. Length >= count * 3. */
    positions: Float32Array;
    /** Per-point intensity values. Length >= count. */
    intensities: Float32Array;
    /** Number of active points in this batch. */
    count: number;
}

export function createPointCloudBuffer() {
    let capacity = 0;
    let positions = new Float32Array(0);
    let intensities = new Float32Array(0);
    let colors = new Float32Array(0);
    let positionAttribute = new BufferAttribute(positions, 3);
    let colorAttribute = new BufferAttribute(colors, 3);

    const geometry = new BufferGeometry();
    geometry.setAttribute('position', positionAttribute);
    geometry.setAttribute('color', colorAttribute);
    geometry.setDrawRange(0, 0);
    geometry.boundingSphere = new Sphere();

    function ensureCapacity(count: number): void {
        if (count <= capacity) return;

        capacity = count;
        positions = new Float32Array(count * 3);
        intensities = new Float32Array(count);
        colors = new Float32Array(count * 3);
        positionAttribute = new BufferAttribute(positions, 3);
        colorAttribute = new BufferAttribute(colors, 3);
        geometry.setAttribute('position', positionAttribute);
        geometry.setAttribute('color', colorAttribute);
    }

    function updatePositions(batch: PointBatch): Box3 | undefined {
        ensureCapacity(batch.count);
        positions.set(batch.positions.subarray(0, batch.count * 3), 0);
        intensities.set(batch.intensities.subarray(0, batch.count), 0);
        positionAttribute.needsUpdate = true;
        geometry.setDrawRange(0, batch.count);

        if (batch.count === 0) return undefined;

        const bounds = computeActiveBounds(positions, batch.count);
        geometry.boundingBox = bounds;
        bounds.getBoundingSphere(geometry.boundingSphere!);
        return bounds;
    }

    function updateColors(
        count: number,
        colorMode: ColorMode,
        intensityRange?: [number, number]
    ): void {
        if (count === 0) return;

        buildColorBuffer(positions, intensities, count, colorMode, colors, intensityRange);
        colorAttribute.needsUpdate = true;
    }

    return {
        geometry,
        updatePositions,
        updateColors,
        dispose: () => geometry.dispose()
    };
}
