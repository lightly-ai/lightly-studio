import { describe, expect, it } from 'vitest';
import type { CameraProjectionView } from '$lib/api/lightly_studio_local/types.gen';
import type { PointBatch } from '$lib/components/PointCloudViewer';
import { createSegmentedPointBatch } from '$lib/hooks/useCloudPointFrame/createSegmentedPointBatch';
import { mergePointBatches } from '$lib/hooks/useCloudPointFrame/mergePointBatches';
import {
    projectCuboid,
    projectCuboidFaces,
    projectCuboidWireframe,
    projectPoint,
    projectPointCloud,
    projectPointCloudData
} from './projectionOverlay';

const projection: CameraProjectionView = {
    width: 100,
    height: 80,
    camera_matrix: [10, 0, 50, 0, 10, 40, 0, 0, 1],
    scene_to_camera: [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
};

describe('projectionOverlay', () => {
    it('keeps camera projections identical when the scene retains separate sensor batches', () => {
        const segments = [
            {
                positions: new Float32Array([0, 0, 2]),
                intensities: new Float32Array([10]),
                count: 1
            },
            {
                positions: new Float32Array([1, 0, 2]),
                intensities: new Float32Array([20]),
                count: 1
            }
        ];
        const packed = mergePointBatches(segments);
        const retained = createSegmentedPointBatch(segments);
        expect(projectPointCloudData(retained, projection, 5000, true)).toEqual(
            projectPointCloudData(packed, projection, 5000, true)
        );
        expect(projectPointCloud(retained, projection)).toEqual(
            projectPointCloud(packed, projection)
        );
    });
    it('projects a point with the camera matrix', () => {
        expect(projectPoint([1, 2, 2], projection)).toEqual({ x: 55, y: 50 });
    });

    it('drops points behind the camera and outside the image', () => {
        expect(projectPoint([0, 0, -1], projection)).toBeNull();
        const batch: PointBatch = {
            positions: new Float32Array([0, 0, 2, 20, 0, 2]),
            intensities: new Float32Array(2),
            count: 2
        };
        expect(projectPointCloud(batch, projection)).toEqual([{ x: 50, y: 40 }]);
    });

    it('filters visible points before limiting the projected point count', () => {
        const batch: PointBatch = {
            positions: new Float32Array([20, 0, 2, 0, 0, 2, 21, 0, 2, 1, 0, 2]),
            intensities: new Float32Array(4),
            count: 4
        };

        expect(projectPointCloudData(batch, projection, 2)).toHaveLength(2);
    });

    it('clips a cuboid edge when the cuboid intersects the image boundary', () => {
        const segments = projectCuboid(
            {
                frame_id: 'scene',
                px: 60,
                py: 0,
                pz: 10,
                qx: 0,
                qy: 0,
                qz: 0,
                qw: 1,
                sx: 30,
                sy: 2,
                sz: 2,
                interpolated: false
            },
            projection
        );

        expect(segments.length).toBeGreaterThan(0);
        expect(segments.some(({ start, end }) => start.x === 100 || end.x === 100)).toBe(true);
    });

    it('does not return segments for a cuboid outside the image', () => {
        const segments = projectCuboid(
            {
                frame_id: 'scene',
                px: 100,
                py: 0,
                pz: 10,
                qx: 0,
                qy: 0,
                qz: 0,
                qw: 1,
                sx: 1,
                sy: 1,
                sz: 1,
                interpolated: false
            },
            projection
        );

        expect(segments).toEqual([]);
    });

    it('keeps a cuboid face when only part of it is in front of the camera', () => {
        const faces = projectCuboidFaces(
            {
                frame_id: 'scene',
                px: 0,
                py: 0,
                pz: 0.5,
                qx: 0,
                qy: 0,
                qz: 0,
                qw: 1,
                sx: 2,
                sy: 2,
                sz: 2,
                interpolated: false
            },
            projection
        );

        expect(faces).toHaveLength(5);
        expect(faces.every((face) => face.length === 4)).toBe(true);
        expect(faces.flat().every(({ x, y }) => Number.isFinite(x) && Number.isFinite(y))).toBe(
            true
        );
    });

    it('keeps the cuboid wireframe when some corners are behind the camera', () => {
        const segments = projectCuboidWireframe(
            {
                frame_id: 'scene',
                px: 0,
                py: 0,
                pz: 0.5,
                qx: 0,
                qy: 0,
                qz: 0,
                qw: 1,
                sx: 2,
                sy: 2,
                sz: 2,
                interpolated: false
            },
            projection
        );

        expect(segments).toHaveLength(8);
        const clippedEdges = segments.filter(({ start, end }) =>
            [start, end].some(({ x, y }) => x === 0 || x === 100 || y === 0 || y === 80)
        );
        expect(clippedEdges).toHaveLength(4);
    });
});
