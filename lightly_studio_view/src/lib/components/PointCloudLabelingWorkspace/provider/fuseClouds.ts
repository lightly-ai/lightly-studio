import { transformPositionsInto, type RigidTransform } from './rigidTransform';

/** One decoded sensor sweep, still in the frame its message declared. */
export interface DecodedCloud {
    /** `header.frame_id` of the sweep's message. */
    readonly frameId: string;
    readonly positions: Float32Array;
    readonly sourcePointCount: number;
}

/**
 * Places every sweep whose frame resolves into the target frame and concatenates them.
 *
 * A sweep whose frame does not resolve is left out rather than placed at the origin: one
 * sensor drawn in the wrong place is harder to notice, and worse to label against, than
 * one sensor missing. `skippedFrameIds` names those so a caller can report them.
 */
export function fuseClouds(
    clouds: readonly DecodedCloud[],
    transforms: ReadonlyMap<string, RigidTransform>
) {
    const placed = clouds.filter((cloud) => transforms.has(cloud.frameId));
    const total = placed.reduce((count, cloud) => count + cloud.positions.length, 0);
    const positions = new Float32Array(total);
    let at = 0;
    for (const cloud of placed) {
        at = transformPositionsInto(positions, at, cloud.positions, transforms.get(cloud.frameId)!);
    }
    return {
        positions,
        // Every sweep read, including any skipped: this is what the sensors produced, which
        // is the number the displayed count is worth comparing against.
        sourcePointCount: clouds.reduce((count, cloud) => count + cloud.sourcePointCount, 0),
        skippedFrameIds: clouds
            .filter((cloud) => !transforms.has(cloud.frameId))
            .map((cloud) => cloud.frameId)
    };
}
