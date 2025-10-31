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
    // Track whether the point is inside (starts as false, toggles with each intersection)
    let inside = false;

    // Iterate through each edge of the polygon
    // i is the current vertex, j is the previous vertex
    // This creates edges: (j,i) for each iteration
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
        // Get coordinates of the current edge's endpoints
        const { x: xi, y: yi } = polygon[i];
        const { x: xj, y: yj } = polygon[j];

        // Calculate the x-coordinate where the edge intersects with the horizontal ray at py
        // Formula derived from linear interpolation: x = x1 + (x2 - x1) * (py - y1) / (y2 - y1)
        const denominator = yj - yi;
        const intersectionX = denominator !== 0 ? ((xj - xi) * (py - yi)) / denominator + xi : xi;

        // Check if the edge crosses the horizontal ray cast from the point
        // Conditions:
        // 1. (yi > py !== yj > py): One endpoint is above py and the other is below (edge crosses horizontally)
        // 2. (px < intersectionX): The point is to the left of the intersection (ray extends to the right)
        const intersects = yi > py !== yj > py && px < intersectionX;

        // Each time the ray crosses an edge, toggle inside/outside status
        if (intersects) {
            inside = !inside;
        }
    }

    // After checking all edges, if we crossed an odd number of edges, we're inside
    return inside;
}
