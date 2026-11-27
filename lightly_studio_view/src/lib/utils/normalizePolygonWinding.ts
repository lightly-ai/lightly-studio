export type PolygonPart = ReadonlyArray<readonly [number, number]>;

/**
 * Returns each part with a non-negative signed area. Parts with a negative
 * area are reversed. The input is not changed.
 */
export const normalizePolygonWinding = (parts: ReadonlyArray<PolygonPart>): PolygonPart[] =>
    parts.map((part) => (getSignedArea(part) < 0 ? [...part].reverse() : part));

const getSignedArea = (part: PolygonPart): number => {
    let doubleArea = 0;
    part.forEach(([x1, y1], index) => {
        const [x2, y2] = part[(index + 1) % part.length];
        doubleArea += x1 * y2 - x2 * y1;
    });
    return doubleArea / 2;
};
