import { derived, get, writable, type Readable } from 'svelte/store';
import { partitionCounts } from './partitionCounts';

export interface SplitRow {
    id: string;
    name: string;
    percentage: number;
}

interface UseSplitFormParams {
    filteredSampleCount: Readable<number>;
}

// Percentages are integers that always sum to exactly 100.
const REQUIRED_SUM = 100;

const DEFAULT_ROWS: SplitRow[] = [
    { id: 'train', name: 'train', percentage: 80 },
    { id: 'val', name: 'val', percentage: 10 },
    { id: 'test', name: 'test', percentage: 10 }
];

export function useSplitForm({ filteredSampleCount }: UseSplitFormParams) {
    const rows = writable<SplitRow[]>(cloneDefaultRows());

    const errorMessage = derived(rows, ($rows) => computeErrorMessage($rows));

    const isValid = derived(errorMessage, ($error) => $error === null);

    // Per-split counts previewed against the current filtered set, using the same
    // largest-remainder method as the backend so the numbers match the result.
    const previewCounts = derived([rows, filteredSampleCount], ([$rows, $count]) =>
        partitionCounts(
            $count,
            Object.fromEntries($rows.map((row) => [row.name, Math.max(row.percentage, 0)]))
        )
    );

    function addRow(): void {
        // Carve the new row's share out of the current last row so the total
        // stays at 100.
        rows.update(($rows) => {
            const last = $rows[$rows.length - 1];
            const take = last ? Math.floor(last.percentage / 2) : 0;
            const next = $rows.map((row, index) =>
                index === $rows.length - 1 ? { ...row, percentage: row.percentage - take } : row
            );
            return [...next, { id: crypto.randomUUID(), name: '', percentage: take }];
        });
    }

    function removeRow(id: string): void {
        // Hand the removed row's share to the following row (wrapping to the
        // first) so the total stays at 100.
        rows.update(($rows) => {
            const index = $rows.findIndex((row) => row.id === id);
            if (index === -1 || $rows.length <= 1) return $rows;

            const donated = $rows[index].percentage;
            const recipientId = $rows[(index + 1) % $rows.length].id;
            return $rows
                .filter((row) => row.id !== id)
                .map((row) =>
                    row.id === recipientId ? { ...row, percentage: row.percentage + donated } : row
                );
        });
    }

    function updateName(id: string, name: string): void {
        rows.update(($rows) => $rows.map((row) => (row.id === id ? { ...row, name } : row)));
    }

    function updatePercentage(id: string, percentage: number): void {
        rows.update(($rows) => rebalanceOnEdit($rows, id, percentage));
    }

    function reset(): void {
        rows.set(cloneDefaultRows());
    }

    function getSizes(): Record<string, number> {
        return Object.fromEntries(get(rows).map((row) => [row.name.trim(), row.percentage]));
    }

    return {
        rows,
        errorMessage,
        isValid,
        previewCounts,
        addRow,
        removeRow,
        updateName,
        updatePercentage,
        reset,
        getSizes
    };
}

// Applies an edit to row `id`, absorbing the delta into the NEXT row (wrapping
// to the first). The edited value is clamped so the neighbour stays within
// [0, 100], which keeps the visible percentages summing to exactly 100.
function rebalanceOnEdit(rows: SplitRow[], id: string, percentage: number): SplitRow[] {
    const index = rows.findIndex((row) => row.id === id);
    if (index === -1) return rows;

    const neighbourIndex = (index + 1) % rows.length;
    // A single row can only ever be 100; nothing to rebalance against.
    if (neighbourIndex === index) return rows;

    const safe = Number.isFinite(percentage) ? percentage : 0;
    const current = rows[index].percentage;
    const neighbour = rows[neighbourIndex].percentage;
    const lower = Math.max(0, current + neighbour - REQUIRED_SUM);
    const upper = Math.min(REQUIRED_SUM, current + neighbour);
    const clamped = Math.min(Math.max(safe, lower), upper);

    return rows.map((row, i) => {
        if (i === index) return { ...row, percentage: clamped };
        if (i === neighbourIndex) return { ...row, percentage: current + neighbour - clamped };
        return row;
    });
}

function cloneDefaultRows(): SplitRow[] {
    return DEFAULT_ROWS.map((row) => ({ ...row }));
}

function computeErrorMessage(rows: SplitRow[]): string | null {
    if (rows.length === 0) return 'Add at least one split.';

    const names = rows.map((row) => row.name.trim());
    if (names.some((name) => name.length === 0)) return 'Every split needs a name.';
    if (new Set(names).size !== names.length) return 'Split names must be unique.';
    if (rows.some((row) => row.percentage <= 0)) return 'Every percentage must be greater than 0.';

    return null;
}
