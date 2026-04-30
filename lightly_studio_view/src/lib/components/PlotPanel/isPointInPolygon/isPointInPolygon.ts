type Point = {
    x: number;
    y: number;
};

/**
 * Checks if a point is inside a polygon using the ray-casting algorithm.
 *
 * The algorithm works by casting a horizontal ray from the test point to infinity
 * and counting how many times it intersects with the polygon's edges. If the count
 * is odd, the point is inside; if even, it's outside.
 *
 * @param px The x-coordinate of the point to test.
 * @param py The y-coordinate of the point to test.
 * @param polygon An array of points representing the vertices of the polygon.
 * @returns True if the point is inside the polygon, false otherwise.
 */
export function isPointInPolygon(px: number, py: number, polygon: Point[]): boolean {
    let inside = false;

    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
        const { x: xi, y: yi } = polygon[i];
        const { x: xj, y: yj } = polygon[j];

        const denominator = yj - yi;
        const intersectionX = denominator !== 0 ? ((xj - xi) * (py - yi)) / denominator + xi : xi;

        const intersects = yi > py !== yj > py && px < intersectionX;

        if (intersects) {
            inside = !inside;
        }
    }

    return inside;
}
