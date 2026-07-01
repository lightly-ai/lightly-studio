import { readonly, writable, type Readable } from 'svelte/store';
import type { ConfusionCell } from '$lib/api/lightly_studio_local';

// Module-level so the confusion-matrix panel (which publishes the clicked cell)
// and the matches grid + sidebar chip (which read it) share one selection.
// null means no confusion-cell filter is active. The cell carries its own
// evaluation_run_id so readers can ignore a cell that belongs to a different run
// than the matches view they render.
const selectedConfusionCell = writable<ConfusionCell | null>(null);

export const selectedMatchConfusionCell: Readable<ConfusionCell | null> =
    readonly(selectedConfusionCell);

export function setMatchConfusionCell(cell: ConfusionCell | null): void {
    selectedConfusionCell.set(cell);
}

export function clearMatchConfusionCell(): void {
    selectedConfusionCell.set(null);
}

export function useMatchConfusionCell() {
    return {
        selectedConfusionCell: selectedMatchConfusionCell,
        set: setMatchConfusionCell,
        clear: clearMatchConfusionCell
    };
}
