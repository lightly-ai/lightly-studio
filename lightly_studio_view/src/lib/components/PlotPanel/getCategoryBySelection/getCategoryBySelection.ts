import type { Point } from 'embedding-atlas/svelte';
import { isPointInPolygon } from '../isPointInPolygon/isPointInPolygon';
import type { ArrowData } from '../useArrowData/useArrowData';
import { REMAINING_CATEGORY } from '../plotCategories';

type Selection = Point[] | null;

/**
 * Creates a reducer function that updates point categories based on selection intersection.
 *
 * @param selection - Polygon selection defining the area to check against
 * @param data - Arrow data containing x and y coordinates as Float32Arrays
 * @returns A reducer function that takes (prevValue: number, index: number) and returns:
 *          - `prevValue` if the point intersects the selection polygon
 *          - `REMAINING_CATEGORY` if the point does not intersect the selection polygon
 *          - `prevValue` if no selection is given
 */
export const getCategoryBySelection =
    (selection: Selection, data: ArrowData) => (prevValue: number, index: number) => {
        if (!selection) {
            return prevValue;
        }
        const x = (data.x as Float32Array)[index];
        const y = (data.y as Float32Array)[index];
        const isIntersected = isPointInPolygon(x, y, selection);
        return isIntersected ? prevValue : REMAINING_CATEGORY;
    };
