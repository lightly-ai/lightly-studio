import { isUnselectableCategory } from '../plotCategories';

const HOVER_RADIUS_PX = 10;

interface CreateQuerySelectionParams {
    x: Float32Array | undefined;
    y: Float32Array | undefined;
    sampleIds: string[] | undefined;
    category: Uint8Array | undefined;
}

interface TooltipDataPoint {
    x: number;
    y: number;
    category?: number;
    identifier: string;
}

/**
 * Builds the `querySelection` callback for the embedding view: given a hover
 * location it returns the nearest selectable point, or null when none is within
 * the hover radius.
 */
export function createQuerySelection(params: CreateQuerySelectionParams) {
    const { x, y, sampleIds, category } = params;
    return async (queryX: number, queryY: number, unitDistance: number) => {
        if (!x || !y || !sampleIds) {
            return null;
        }
        const maxDistance = HOVER_RADIUS_PX * unitDistance;
        let nearestIndex = -1;
        let nearestDistanceSq = maxDistance * maxDistance;
        for (let index = 0; index < x.length; index++) {
            if (category && isUnselectableCategory(category[index])) {
                continue;
            }
            const dx = x[index] - queryX;
            const dy = y[index] - queryY;
            const distanceSq = dx * dx + dy * dy;
            if (distanceSq < nearestDistanceSq) {
                nearestDistanceSq = distanceSq;
                nearestIndex = index;
            }
        }
        if (nearestIndex === -1) {
            return null;
        }
        const point: TooltipDataPoint = {
            x: x[nearestIndex],
            y: y[nearestIndex],
            category: category?.[nearestIndex],
            identifier: sampleIds[nearestIndex]
        };
        return point;
    };
}
