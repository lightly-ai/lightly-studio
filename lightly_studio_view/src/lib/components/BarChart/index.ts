export { default as BarChart } from './BarChart.svelte';
export type { CategoryCount, CategoryCountSeries } from './types';
export type { BarChartOrientation, BarChartValueMode } from './buildEchartsOption';
// Shared with the Histogram so grouped bars and grouped bins line up and a
// sample tag keeps one color across both chart types.
export { GROUPED_GRID_TOP_PX } from './buildEchartsOption';
export { assignSeriesColors } from './seriesColors';
