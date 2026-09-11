import {
    composeTransforms,
    IDENTITY_TRANSFORM,
    invertTransform,
    rigidTransform,
    type RigidTransform
} from './rigidTransform';

/** A `tf2_msgs/msg/TFMessage`, as `/tf_static` publishes sensor extrinsics. */
export interface TransformMessage {
    readonly transforms: readonly {
        readonly header: { readonly frame_id: string };
        readonly child_frame_id: string;
        readonly transform: {
            readonly translation: { readonly x: number; readonly y: number; readonly z: number };
            readonly rotation: {
                readonly x: number;
                readonly y: number;
                readonly z: number;
                readonly w: number;
            };
        };
    }[];
}

/** Frame -> its neighbours, each with the transform of that neighbour into the frame. */
export type TransformGraph = ReadonlyMap<string, readonly (readonly [string, RigidTransform])[]>;

/**
 * Builds the undirected frame graph published on `/tf_static`.
 *
 * Both directions are stored so any frame can serve as the target: TF publishes
 * parent-to-child, and a sensor is usually the child of the frame we want to render in.
 * Edges whose transform is unusable are dropped, leaving that frame unreachable rather
 * than misplaced.
 */
export function buildTransformGraph(messages: readonly TransformMessage[]): TransformGraph {
    const graph = new Map<string, (readonly [string, RigidTransform])[]>();
    for (const message of messages) {
        for (const entry of message.transforms ?? []) {
            const { translation, rotation } = entry.transform;
            const parentFromChild = rigidTransform(
                [translation.x, translation.y, translation.z],
                [rotation.x, rotation.y, rotation.z, rotation.w]
            );
            const parent = entry.header?.frame_id;
            const child = entry.child_frame_id;
            if (!parentFromChild || !parent || !child) continue;
            addEdge(graph, parent, child, parentFromChild);
            addEdge(graph, child, parent, invertTransform(parentFromChild));
        }
    }
    return graph;
}

/**
 * Resolves `target_from_frame` for every frame connected to `targetFrameId`.
 *
 * Breadth-first, so each frame takes the shortest chain of published transforms. The
 * target itself always resolves to the identity, which is what lets a recording with no
 * usable `/tf_static` still render the frames already expressed in the target.
 */
export function resolveTransforms(
    graph: TransformGraph,
    targetFrameId: string
): ReadonlyMap<string, RigidTransform> {
    const resolved = new Map<string, RigidTransform>([[targetFrameId, IDENTITY_TRANSFORM]]);
    const queue = [targetFrameId];
    while (queue.length > 0) {
        const frame = queue.shift()!;
        const targetFromFrame = resolved.get(frame)!;
        for (const [neighbour, frameFromNeighbour] of graph.get(frame) ?? []) {
            if (resolved.has(neighbour)) continue;
            resolved.set(neighbour, composeTransforms(targetFromFrame, frameFromNeighbour));
            queue.push(neighbour);
        }
    }
    return resolved;
}

function addEdge(
    graph: Map<string, (readonly [string, RigidTransform])[]>,
    from: string,
    to: string,
    transform: RigidTransform
): void {
    graph.set(from, [...(graph.get(from) ?? []), [to, transform]]);
}
