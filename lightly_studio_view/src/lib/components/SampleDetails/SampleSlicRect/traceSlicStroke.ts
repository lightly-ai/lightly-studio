interface Point {
    x: number;
    y: number;
}

export function traceSlicStroke(from: Point, to: Point): Point[] {
    const crossings = [0, 1];
    for (const axis of ['x', 'y'] as const) {
        const delta = to[axis] - from[axis];
        if (!delta) continue;
        const firstEdge = Math.floor(Math.min(from[axis], to[axis])) + 1;
        for (let edge = firstEdge; edge < Math.max(from[axis], to[axis]); edge++) {
            crossings.push((edge - from[axis]) / delta);
        }
    }
    crossings.sort((a, b) => a - b);
    // Sample between every grid crossing, including arbitrarily short corner crossings.
    const points = crossings.slice(1).map((end, i) => {
        const t = (crossings[i] + end) / 2;
        return { x: from.x + (to.x - from.x) * t, y: from.y + (to.y - from.y) * t };
    });
    return [...points, to];
}
