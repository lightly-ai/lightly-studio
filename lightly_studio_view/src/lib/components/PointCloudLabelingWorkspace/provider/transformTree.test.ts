import { describe, expect, it } from 'vitest';
import { buildTransformGraph, resolveTransforms, type TransformMessage } from './transformTree';

function edge(parent: string, child: string, x: number, y = 0, z = 0) {
    return {
        header: { frame_id: parent },
        child_frame_id: child,
        transform: { translation: { x, y, z }, rotation: { x: 0, y: 0, z: 0, w: 1 } }
    };
}

function tf(...transforms: ReturnType<typeof edge>[]): TransformMessage {
    return { transforms };
}

describe('resolveTransforms', () => {
    it('places a sensor published as a child of the target frame', () => {
        const graph = buildTransformGraph([tf(edge('CABIN', 'lidar_rear_left', -2, 1))]);

        const transforms = resolveTransforms(graph, 'CABIN');

        expect(transforms.get('lidar_rear_left')!.translation).toEqual([-2, 1, 0]);
    });

    it('inverts a transform published towards the target frame', () => {
        const graph = buildTransformGraph([tf(edge('lidar_front', 'CABIN', 3))]);

        const transforms = resolveTransforms(graph, 'CABIN');

        expect(transforms.get('lidar_front')!.translation).toEqual([-3, 0, 0]);
    });

    it('follows a chain of frames to the target', () => {
        const graph = buildTransformGraph([
            tf(edge('CABIN', 'mount', 1), edge('mount', 'lidar_front', 0, 2))
        ]);

        const transforms = resolveTransforms(graph, 'CABIN');

        expect(transforms.get('lidar_front')!.translation).toEqual([1, 2, 0]);
    });

    it('resolves the target itself, so a recording without transforms still renders', () => {
        const transforms = resolveTransforms(buildTransformGraph([]), 'lidar');

        expect([...transforms.keys()]).toEqual(['lidar']);
        expect(transforms.get('lidar')!.translation).toEqual([0, 0, 0]);
    });

    it('leaves a frame the transforms never mention unresolved', () => {
        const graph = buildTransformGraph([tf(edge('CABIN', 'lidar_front', 1))]);

        expect(resolveTransforms(graph, 'CABIN').has('lidar_rear_left')).toBe(false);
    });

    it('drops an edge whose transform cannot describe a pose', () => {
        const broken = {
            header: { frame_id: 'CABIN' },
            child_frame_id: 'lidar_front',
            transform: {
                translation: { x: 1, y: 0, z: 0 },
                rotation: { x: 0, y: 0, z: 0, w: 0 }
            }
        };

        expect(resolveTransforms(buildTransformGraph([tf(broken)]), 'CABIN').size).toBe(1);
    });

    it('reads every /tf_static message, not only the first', () => {
        const graph = buildTransformGraph([
            tf(edge('CABIN', 'lidar_front', 1)),
            tf(edge('CABIN', 'lidar_rear_left', -2))
        ]);

        expect(resolveTransforms(graph, 'CABIN').size).toBe(3);
    });
});
