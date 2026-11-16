import { describe, expect, it, vi } from 'vitest';
import type { BufferAttribute, BufferGeometry } from 'three';
import { createSegmentedPointBatch } from '$lib/hooks/useCloudPointFrame/createSegmentedPointBatch';
import { createPointCloudFrameBuffers } from './createPointCloudFrameBuffers';

const frame = (x: number) => ({
    positions: new Float32Array([x, 0, 0, x + 1, 1, 1]),
    intensities: new Float32Array([0, 1]),
    count: 2
});

describe('retained sensor geometries', () => {
    it('uploads only the entering frame and releases frames leaving the accumulation window', () => {
        const buffers = createPointCloudFrameBuffers();
        const [first, retained, next] = [frame(0), frame(2), frame(4)];
        const initial = buffers.update(createSegmentedPointBatch([first, retained]), 'intensity');
        const disposeFirst = vi.fn();
        const disposeRetained = vi.fn();
        initial.geometries[0].addEventListener('dispose', disposeFirst);
        initial.geometries[1].addEventListener('dispose', disposeRetained);
        const positionVersion = attributeVersion(initial.geometries[1], 'position');
        const colorVersion = attributeVersion(initial.geometries[1], 'color');

        const updated = buffers.update(createSegmentedPointBatch([retained, next]), 'intensity');
        expect(updated.geometries[0]).toBe(initial.geometries[1]);
        expect(attributeVersion(updated.geometries[0], 'position')).toBe(positionVersion);
        expect(attributeVersion(updated.geometries[0], 'color')).toBe(colorVersion);
        expect(disposeFirst).toHaveBeenCalledOnce();
        expect(disposeRetained).not.toHaveBeenCalled();
        expect(updated.bounds?.min.toArray()).toEqual([2, 0, 0]);
        expect(updated.bounds?.max.toArray()).toEqual([5, 1, 1]);
        expect(Array.from(updated.geometries[1].getAttribute('position').array)).toEqual(
            Array.from(next.positions)
        );

        buffers.dispose();
        expect(disposeRetained).toHaveBeenCalledOnce();
        expect(disposeFirst).toHaveBeenCalledOnce();
    });

    it('colors each segment from the provided camera-rgb colors', () => {
        const buffers = createPointCloudFrameBuffers();
        const cameraColors = new Float32Array([1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1, 0]);
        const result = buffers.update(
            createSegmentedPointBatch([frame(0), frame(2)]),
            'camera-rgb',
            undefined,
            cameraColors
        );
        expect(Array.from(result.geometries[0].getAttribute('color').array)).toEqual([
            1, 0, 0, 0, 1, 0
        ]);
        expect(Array.from(result.geometries[1].getAttribute('color').array)).toEqual([
            0, 0, 1, 1, 1, 0
        ]);
        buffers.dispose();
    });

    it('recolors retained frames when the window-wide intensity range changes', () => {
        const buffers = createPointCloudFrameBuffers();
        const retained = frame(0);
        const initial = buffers.update(retained, 'intensity');
        const version = attributeVersion(initial.geometries[0], 'color');
        const next = { ...frame(2), intensities: new Float32Array([0, 10]) };
        const updated = buffers.update(createSegmentedPointBatch([retained, next]), 'intensity');
        expect(updated.geometries[0]).toBe(initial.geometries[0]);
        expect(attributeVersion(updated.geometries[0], 'color')).toBeGreaterThan(version);
        buffers.dispose();
    });
});

function attributeVersion(geometry: BufferGeometry, name: string): number {
    return (geometry.getAttribute(name) as BufferAttribute).version;
}
