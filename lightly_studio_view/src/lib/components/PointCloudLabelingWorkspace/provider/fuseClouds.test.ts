import { describe, expect, it } from 'vitest';
import { fuseClouds } from './fuseClouds';
import { buildTransformGraph, resolveTransforms } from './transformTree';

const transforms = resolveTransforms(
    buildTransformGraph([
        {
            transforms: [
                {
                    header: { frame_id: 'CABIN' },
                    child_frame_id: 'lidar_rear_left',
                    transform: {
                        translation: { x: -2, y: 1, z: 0.5 },
                        rotation: { x: 0, y: 0, z: 0, w: 1 }
                    }
                }
            ]
        }
    ]),
    'CABIN'
);

const cabinCloud = {
    frameId: 'CABIN',
    positions: new Float32Array([1, 1, 1]),
    sourcePointCount: 1
};
const sensorCloud = {
    frameId: 'lidar_rear_left',
    positions: new Float32Array([0, 0, 0]),
    sourcePointCount: 3
};

describe('fuseClouds', () => {
    it('places each sweep where its sensor sits and concatenates them', () => {
        const fused = fuseClouds([cabinCloud, sensorCloud], transforms);

        expect([...fused.positions]).toEqual([1, 1, 1, -2, 1, 0.5]);
    });

    it('counts every point the sensors produced, not only the drawn ones', () => {
        expect(fuseClouds([cabinCloud, sensorCloud], transforms).sourcePointCount).toBe(4);
    });

    it('leaves out a sweep whose frame is unknown, and names it', () => {
        const orphan = {
            frameId: 'lidar_roof',
            positions: new Float32Array([9, 9, 9]),
            sourcePointCount: 1
        };

        const fused = fuseClouds([cabinCloud, orphan], transforms);

        expect([...fused.positions]).toEqual([1, 1, 1]);
        expect(fused.skippedFrameIds).toEqual(['lidar_roof']);
    });

    it('returns an empty frame rather than failing when nothing can be placed', () => {
        const fused = fuseClouds(
            [{ frameId: 'unknown', positions: new Float32Array([1, 2, 3]), sourcePointCount: 1 }],
            transforms
        );

        expect(fused.positions).toHaveLength(0);
        expect(fused.sourcePointCount).toBe(1);
    });
});
