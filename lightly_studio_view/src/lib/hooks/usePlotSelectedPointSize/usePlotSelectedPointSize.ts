import { writable } from 'svelte/store';

export const PLOT_SELECTED_POINT_SIZE_STORAGE_KEY = 'lightly-studio:plot-selected-point-size';

export const PLOT_SELECTED_POINT_SIZES = [
    { value: 'small', label: 'Small' },
    { value: 'medium', label: 'Medium' },
    { value: 'large', label: 'Large' },
    { value: 'extra_large', label: 'Extra large' }
] as const;

export type PlotSelectedPointSize = (typeof PLOT_SELECTED_POINT_SIZES)[number]['value'];

const DEFAULT_SIZE: PlotSelectedPointSize = 'large';

function isPlotSelectedPointSize(value: unknown): value is PlotSelectedPointSize {
    return PLOT_SELECTED_POINT_SIZES.some((size) => size.value === value);
}

function readStoredSize(): PlotSelectedPointSize {
    try {
        const stored = localStorage.getItem(PLOT_SELECTED_POINT_SIZE_STORAGE_KEY);
        return isPlotSelectedPointSize(stored) ? stored : DEFAULT_SIZE;
    } catch {
        return DEFAULT_SIZE;
    }
}

const selectedPointSize = writable<PlotSelectedPointSize>(readStoredSize());
selectedPointSize.subscribe((value) => {
    try {
        localStorage.setItem(PLOT_SELECTED_POINT_SIZE_STORAGE_KEY, value);
    } catch {
        // The size still applies for this session when storage is unavailable.
    }
});

/**
 * The size of the selected points in the embedding plot. It is a browser preference, so it is
 * kept in localStorage rather than in the backend settings, and applies as soon as it changes.
 */
export function usePlotSelectedPointSize() {
    return { selectedPointSize };
}
