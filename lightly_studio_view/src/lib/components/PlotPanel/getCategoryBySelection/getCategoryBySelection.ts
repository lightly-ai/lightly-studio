import type { Point } from 'embedding-atlas/svelte';
import { isPointInPolygon } from '../isPointInPolygon/isPointInPolygon';
import type { ArrowData } from '../useArrowData/useArrowData';
import { EXCLUDED_BY_FILTERS_CATEGORY } from '../plotCategories';

type Selection = Point[] | null;

/**
 * Creates a reducer function that updates point categories based on selection intersection.
 *
 * @param selection - Polygon selection defining the area to check against
 * @param data - Arrow data containing x and y coordinates as Float32Arrays
 * @param outsideCategory - Category assigned to points outside the selection (defaults to
 *        `EXCLUDED_BY_FILTERS_CATEGORY`)
 * @returns A reducer function that takes (prevValue: number, index: number) and returns:
 *          - `prevValue` if the point intersects the selection polygon
 *          - `outsideCategory` if the point does not intersect the selection polygon
 *          - `prevValue` if no selection is given
 */
export const getCategoryBySelection =
    (
        selection: Selection,
        data: ArrowData,
        outsideCategory: number = EXCLUDED_BY_FILTERS_CATEGORY
    ) =>
    (prevValue: number, index: number) => {
        if (!selection) {
            return prevValue;
        }
        const x = (data.x as Float32Array)[index];
        const y = (data.y as Float32Array)[index];
        const isIntersected = isPointInPolygon(x, y, selection);
        return isIntersected ? prevValue : outsideCategory;
    };
