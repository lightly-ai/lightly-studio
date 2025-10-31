import type { Point } from 'embedding-atlas/svelte';
import { isPointInPolygon } from '../isPointInPolygon/isPointInPolygon';
import type { ArrowData } from '../useArrowData/useArrowData';

type Selection = Point[] | null;

/**
 * Creates a reducer function that updates point categories based on selection intersection.
 *
 * @param selection - Polygon selection defining the area to check against
 * @param data - Arrow data containing x and y coordinates as Float32Arrays
 * @returns A reducer function that takes (prevValue: number, index: number) and returns:
 *          - `2` if prevValue is `1` AND the point at index intersects the selection polygon
 *          - `prevValue` otherwise (unchanged if no selection or point doesn't meet criteria)
 *
 * @example
 * const categoryReducer = getCategoryBySelection(polygonSelection, arrowData);
 * const updatedCategories = categories.reduce(categoryReducer, initialValue);
 */
export const getCategoryBySelection =
    (selection: Selection, data: ArrowData) => (prevValue: number, index: number) => {
        if (!selection) {
            return prevValue;
        }
        const x = (data.x as Float32Array)[index];
        const y = (data.y as Float32Array)[index];
        const isIntersected = isPointInPolygon(x, y, selection);
        return prevValue == 1 && isIntersected ? 2 : prevValue;
    };
