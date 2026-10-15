import { describe, expect, it } from 'vitest';
import { buildCuboidTransformPayload } from './cuboidTransform';
import type { CuboidAnnotation } from '$lib/components/PointCloudLabelingWorkspace/domain';

function fakeObj(
    position: [number, number, number] = [0, 0, 0],
    quaternion: [number, number, number, number] = [0, 0, 0, 1],
    scale: [number, number, number] = [1, 1, 1]
) {
    return {
        position: { x: position[0], y: position[1], z: position[2] },
        quaternion: { x: quaternion[0], y: quaternion[1], z: quaternion[2], w: quaternion[3] },
        scale: {
            x: scale[0],
            y: scale[1],
            z: scale[2],
            set(x: number, y: number, z: number) {
                this.x = x;
                this.y = y;
                this.z = z;
            }
        }
    } as Parameters<typeof buildCuboidTransformPayload>[1];
}

const ANNOTATION: CuboidAnnotation = {
    id: 'ann-1',
    frameId: 'frame-1',
    coordinateFrame: { id: 'ego', convention: 'right-handed-x-forward-y-left-z-up', unit: 'meter' },
    annotationClassId: 'class-1',
    annotationSourceId: 'source-1',
    trackId: null,
    trackNumber: null,
    parentTrackNumber: null,
    keyframeId: null,
    center: [1, 2, 3],
    size: [2, 3, 4],
    rotation: [0, 0, 0, 1]
};

describe('buildCuboidTransformPayload', () => {
    it('uses annotation.size when no currentSize is provided', () => {
        const obj = fakeObj([5, 6, 7], [0, 0, 0, 1], [1.5, 2, 0.5]);

        const result = buildCuboidTransformPayload(ANNOTATION, obj);

        expect(result.size).toEqual([3, 6, 2]);
    });

    it('uses currentSize instead of annotation.size when provided', () => {
        const obj = fakeObj([5, 6, 7], [0, 0, 0, 1], [1.5, 2, 0.5]);

        const result = buildCuboidTransformPayload(ANNOTATION, obj, [10, 20, 30]);

        expect(result.size).toEqual([15, 40, 15]);
    });

    it('resets obj.scale to (1,1,1) after reading it', () => {
        const obj = fakeObj([0, 0, 0], [0, 0, 0, 1], [3, 4, 5]);

        buildCuboidTransformPayload(ANNOTATION, obj);

        expect(obj.scale.x).toBe(1);
        expect(obj.scale.y).toBe(1);
        expect(obj.scale.z).toBe(1);
    });

    it('accumulates size correctly across successive calls with currentSize', () => {
        const first = buildCuboidTransformPayload(
            ANNOTATION,
            fakeObj([0, 0, 0], [0, 0, 0, 1], [1.5, 1, 1])
        );
        expect(first.size).toEqual([3, 3, 4]);

        const second = buildCuboidTransformPayload(
            ANNOTATION,
            fakeObj([0, 0, 0], [0, 0, 0, 1], [2, 1, 1]),
            first.size
        );
        expect(second.size).toEqual([6, 3, 4]);
    });
});
