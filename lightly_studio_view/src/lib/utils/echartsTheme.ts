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
