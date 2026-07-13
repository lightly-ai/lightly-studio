// Shared dark-theme constants for ECharts option builders. ECharts renders to a
// canvas, so it can't use CSS classes/variables — these mirror the Tailwind
// gray palette as literals (gray-400 for text, gray-700 for lines).

/** Muted gray for axis labels and axis names (Tailwind gray-400). */
export const CHART_TEXT_COLOR = '#9ca3af';

/** Axis and split line color (Tailwind gray-700). */
export const CHART_LINE_COLOR = '#374151';

/** Default axis label style shared across charts. */
export const CHART_AXIS_LABEL = { color: CHART_TEXT_COLOR, fontSize: 12 } as const;

/** Hover emphasis shadow shared across chart series. */
export const CHART_EMPHASIS = {
    itemStyle: { shadowBlur: 6, shadowColor: 'rgba(0,0,0,0.3)' }
} as const;

/**
 * Qualitative palette for overlaid distribution series (one color per compared
 * tag). Index 0 is the Lightly primary green so a single series keeps its
 * familiar look; the rest are picked for contrast in both themes.
 */
export const SERIES_COLOR_PALETTE = [
    'rgba(59,217,159,0.85)', // Lightly green
    'rgba(96,165,250,0.85)', // blue-400
    'rgba(251,146,60,0.85)', // orange-400
    'rgba(196,131,255,0.85)', // purple-400
    'rgba(244,114,182,0.85)', // pink-400
    'rgba(250,204,21,0.85)', // yellow-400
    'rgba(45,212,191,0.85)', // teal-400
    'rgba(248,113,113,0.85)' // red-400
] as const;

/** Color for the series at `index`, cycling through {@link SERIES_COLOR_PALETTE}. */
export const getSeriesColor = (index: number): string =>
    SERIES_COLOR_PALETTE[index % SERIES_COLOR_PALETTE.length];
