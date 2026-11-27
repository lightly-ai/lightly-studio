import type { Vector3 } from '../domain';
import { getFlatDistance } from './egoRange';

export interface EgoDistanceLine {
    start: Vector3;
    end: Vector3;
    labelPosition: Vector3;
    /** Flat distance from the ego to the target, in meters. The label shows it. */
    meters: number;
    /** Drawn length of the line in 3D, in meters. The dashes need it. */
    length: number;
}

/** Returns a line from the ego origin to a target point, with the flat distance between them. */
export function getEgoDistanceLine(egoPosition: Vector3, target: Vector3): EgoDistanceLine {
    return {
        start: egoPosition,
        end: target,
        labelPosition: [
            (egoPosition[0] + target[0]) / 2,
            (egoPosition[1] + target[1]) / 2,
            (egoPosition[2] + target[2]) / 2
        ],
        meters: getFlatDistance(target, egoPosition),
        length: Math.hypot(
            target[0] - egoPosition[0],
            target[1] - egoPosition[1],
            target[2] - egoPosition[2]
        )
    };
}
