import { describe, expect, it } from 'vitest';
import { Object3D } from 'three';
import {
    buildCuboidTransformPayload,
    captureTransformSnapshot,
    restoreTransformSnapshot
} from './cuboidTransform';
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
    parentTrackClassName: null,
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

describe('captureTransformSnapshot', () => {
    it('clones position, quaternion, and scale from the object', () => {
        const obj = new Object3D();
        obj.position.set(1, 2, 3);
        obj.quaternion.set(0.1, 0.2, 0.3, 0.9);
        obj.scale.set(1.5, 2, 0.5);

        const snapshot = captureTransformSnapshot(obj);

        expect(snapshot.position.toArray()).toEqual([1, 2, 3]);
        expect(snapshot.quaternion.toArray()).toEqual([0.1, 0.2, 0.3, 0.9]);
        expect(snapshot.scale.toArray()).toEqual([1.5, 2, 0.5]);
    });

    it('returns independent clones that are not affected by later mutations', () => {
        const obj = new Object3D();
        obj.position.set(1, 2, 3);
        obj.quaternion.set(0, 0, 0, 1);
        obj.scale.set(1, 1, 1);

        const snapshot = captureTransformSnapshot(obj);
        obj.position.set(10, 20, 30);
        obj.quaternion.set(0.5, 0.5, 0.5, 0.5);
        obj.scale.set(3, 3, 3);

        expect(snapshot.position.toArray()).toEqual([1, 2, 3]);
        expect(snapshot.quaternion.toArray()).toEqual([0, 0, 0, 1]);
        expect(snapshot.scale.toArray()).toEqual([1, 1, 1]);
    });
});

describe('restoreTransformSnapshot', () => {
    it('restores position, quaternion, and scale on the object', () => {
        const obj = new Object3D();
        obj.position.set(1, 2, 3);
        obj.quaternion.set(0, 0, 0, 1);
        obj.scale.set(1.5, 2, 0.5);
        const snapshot = captureTransformSnapshot(obj);

        obj.position.set(10, 20, 30);
        obj.quaternion.set(0.5, 0.5, 0.5, 0.5);
        obj.scale.set(3, 3, 3);
        restoreTransformSnapshot(obj, snapshot);

        expect(obj.position.toArray()).toEqual([1, 2, 3]);
        expect(obj.quaternion.toArray()).toEqual([0, 0, 0, 1]);
        expect(obj.scale.toArray()).toEqual([1.5, 2, 0.5]);
    });
});
