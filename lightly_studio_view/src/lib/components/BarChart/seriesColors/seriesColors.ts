// Same Tableau 10 palette used by the Histogram component.
export const SERIES_COLORS = [
    '#4E79A7',
    '#F28E2B',
    '#59A14F',
    '#E15759',
    '#B07AA1',
    '#76B7B2',
    '#EDC948',
    '#FF9DA7',
    '#9C755F',
    '#BAB0AC'
];

/** Generates additional opaque colors beyond the base palette. */
export function extendedSeriesColor(index: number): string {
    if (index < SERIES_COLORS.length) return SERIES_COLORS[index];

    const hue = (index * 137.508) % 360;
    return `hsl(${hue} 60% 55%)`;
}

/** Maps a stable series ID to the same accessible chart colour across renders. */
export function colorForSeries(id: string): string {
    const index = [...id].reduce(
        (value, character) => (value * 31 + character.charCodeAt(0)) % SERIES_COLORS.length,
        0
    );
    return SERIES_COLORS[index];
}

/** Resolves hash collisions so simultaneously visible series always differ. */
export function assignSeriesColors(seriesIds: string[]): Map<string, string> {
    const colors = new Map<string, string>();
    const usedColors = new Set<string>();
    for (const id of seriesIds) {
        let index = SERIES_COLORS.indexOf(colorForSeries(id));
        let cycle = 0;
        while (usedColors.has(extendedSeriesColor(index + cycle * SERIES_COLORS.length))) {
            if (index + 1 < SERIES_COLORS.length) {
                index++;
            } else {
                index = 0;
                cycle++;
            }
        }
        const color = extendedSeriesColor(index + cycle * SERIES_COLORS.length);
        colors.set(id, color);
        usedColors.add(color);
    }
    return colors;
}
