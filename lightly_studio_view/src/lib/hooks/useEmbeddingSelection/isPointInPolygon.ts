type Point = {
    x: number;
    y: number;
};

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
