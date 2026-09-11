import { describe, expect, it, vi } from 'vitest';
import {
    addCuboidDuplicateListeners,
    computeDuplicateCenter,
    duplicateCuboid
} from './cuboidDuplication';
import { canonicalCoordinateFrame } from '$lib/components/PointCloudLabelingWorkspace/domain';

type CuboidAnnotation = Parameters<typeof duplicateCuboid>[0];

const FRAME = canonicalCoordinateFrame('lidar-0');

const BASE: CuboidAnnotation = {
    id: 'ann-0',
    frameId: 'frame-0',
    coordinateFrame: FRAME,
    annotationClassId: 'vehicle',
    annotationSourceId: 'ground-truth',
    trackId: null,
    keyframeId: null,
    center: [0, 0, 0],
    size: [4, 2, 2],
    rotation: [0, 0, 0, 1]
};

// 90° yaw around z: [0, 0, sin(45°), cos(45°)]
const HALF = Math.sin(Math.PI / 4);
const YAW_90: CuboidAnnotation['rotation'] = [0, 0, HALF, HALF];

describe('computeDuplicateCenter', () => {
    it('offsets along world +x for identity rotation', () => {
        const [x, y, z] = computeDuplicateCenter(BASE);
        expect(x).toBeCloseTo(4); // offset = size[0] = 4
        expect(y).toBeCloseTo(0);
        expect(z).toBeCloseTo(0);
    });

    it('offsets along world +y after 90° z-rotation', () => {
        // With 90° CCW yaw around z, local +x maps to world +y (left direction in x-fwd/y-left/z-up)
        const [x, y, z] = computeDuplicateCenter({ ...BASE, rotation: YAW_90 });
        expect(x).toBeCloseTo(0);
        expect(y).toBeCloseTo(4); // offset = size[0] = 4 along +y
        expect(z).toBeCloseTo(0);
    });

    it('uses the x-size as the offset distance', () => {
        const [x] = computeDuplicateCenter({ ...BASE, size: [8, 2, 2] });
        expect(x).toBeCloseTo(8);
    });

    it('adds offset to a non-origin center', () => {
        const [x, y, z] = computeDuplicateCenter({ ...BASE, center: [5, 3, 1] });
        expect(x).toBeCloseTo(9); // 5 + 4
        expect(y).toBeCloseTo(3);
        expect(z).toBeCloseTo(1);
    });

    it('preserves z from the original center', () => {
        const [, , z] = computeDuplicateCenter({ ...BASE, center: [0, 0, 5] });
        expect(z).toBeCloseTo(5);
    });
});

describe('duplicateCuboid', () => {
    it('assigns a new ID', () => {
        expect(duplicateCuboid(BASE).id).not.toBe(BASE.id);
    });

    it('copies class, size, and rotation from original', () => {
        const dup = duplicateCuboid(BASE);
        expect(dup.annotationClassId).toBe(BASE.annotationClassId);
        expect(dup.size).toEqual(BASE.size);
        expect(dup.rotation).toEqual(BASE.rotation);
    });

    it('copies frameId, coordinateFrame, and annotationSourceId', () => {
        const dup = duplicateCuboid(BASE);
        expect(dup.frameId).toBe(BASE.frameId);
        expect(dup.coordinateFrame).toEqual(BASE.coordinateFrame);
        expect(dup.annotationSourceId).toBe(BASE.annotationSourceId);
    });

    it('preserves trackId and keyframeId', () => {
        const duplicate = duplicateCuboid({ ...BASE, trackId: 'track-0', keyframeId: 'kf-0' });
        expect(duplicate.trackId).toBe('track-0');
        expect(duplicate.keyframeId).toBe('kf-0');
    });

    it('places center offset from original along local +x', () => {
        const dup = duplicateCuboid(BASE);
        expect(dup.center).not.toEqual(BASE.center);
        expect(dup.center[0]).toBeCloseTo(BASE.center[0] + BASE.size[0]);
    });
});

describe('addCuboidDuplicateListeners', () => {
    it('fires oncreate on Ctrl+D when a cuboid is selected', () => {
        const oncreate = vi.fn();
        const cleanup = addCuboidDuplicateListeners({ selectedAnnotation: BASE, oncreate });

        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'd', ctrlKey: true }));

        expect(oncreate).toHaveBeenCalledTimes(1);
        cleanup();
    });

    it('fires oncreate on Meta+D when a cuboid is selected', () => {
        const oncreate = vi.fn();
        const cleanup = addCuboidDuplicateListeners({ selectedAnnotation: BASE, oncreate });

        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'd', metaKey: true }));

        expect(oncreate).toHaveBeenCalledTimes(1);
        cleanup();
    });

    it('passes a duplicate of the selected annotation to oncreate', () => {
        const oncreate = vi.fn();
        const cleanup = addCuboidDuplicateListeners({ selectedAnnotation: BASE, oncreate });

        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'd', ctrlKey: true }));

        const arg: CuboidAnnotation = oncreate.mock.calls[0][0];
        expect(arg.id).not.toBe(BASE.id);
        expect(arg.annotationClassId).toBe(BASE.annotationClassId);
        expect(arg.size).toEqual(BASE.size);
        expect(arg.rotation).toEqual(BASE.rotation);
        cleanup();
    });

    it('does not fire when no cuboid is selected', () => {
        const oncreate = vi.fn();
        const cleanup = addCuboidDuplicateListeners({ selectedAnnotation: null, oncreate });

        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'd', ctrlKey: true }));

        expect(oncreate).not.toHaveBeenCalled();
        cleanup();
    });

    it('selects the created duplicate', () => {
        const oncreate = vi.fn();
        const onselect = vi.fn();
        const cleanup = addCuboidDuplicateListeners({
            selectedAnnotation: BASE,
            oncreate,
            onselect
        });

        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'd', ctrlKey: true }));

        expect(onselect).toHaveBeenCalledWith(oncreate.mock.calls[0][0].id);
        cleanup();
    });

    it('does not fire on bare D without modifier', () => {
        const oncreate = vi.fn();
        const cleanup = addCuboidDuplicateListeners({ selectedAnnotation: BASE, oncreate });

        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'd' }));

        expect(oncreate).not.toHaveBeenCalled();
        cleanup();
    });

    it('does not fire on unrelated keys with modifier', () => {
        const oncreate = vi.fn();
        const cleanup = addCuboidDuplicateListeners({ selectedAnnotation: BASE, oncreate });

        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Delete', ctrlKey: true }));

        expect(oncreate).not.toHaveBeenCalled();
        cleanup();
    });

    it('stops firing after cleanup', () => {
        const oncreate = vi.fn();
        const cleanup = addCuboidDuplicateListeners({ selectedAnnotation: BASE, oncreate });

        cleanup();
        window.dispatchEvent(new KeyboardEvent('keydown', { key: 'd', ctrlKey: true }));

        expect(oncreate).not.toHaveBeenCalled();
    });
});
