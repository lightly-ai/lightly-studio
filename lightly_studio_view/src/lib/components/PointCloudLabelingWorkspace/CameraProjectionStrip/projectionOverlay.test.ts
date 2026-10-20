import { describe, expect, it } from 'vitest';
import type { CameraProjectionView } from '$lib/api/lightly_studio_local/types.gen';
import type { PointBatch } from '$lib/components/PointCloudViewer';
import { projectCuboid, projectPoint, projectPointCloud } from './projectionOverlay';

const projection: CameraProjectionView = {
    width: 100,
    height: 80,
    camera_matrix: [10, 0, 50, 0, 10, 40, 0, 0, 1],
    scene_to_camera: [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
};

describe('projectionOverlay', () => {
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
});
