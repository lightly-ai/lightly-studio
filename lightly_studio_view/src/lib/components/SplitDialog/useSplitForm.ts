import { derived, get, writable, type Readable } from 'svelte/store';
import { partitionCounts } from './partitionCounts';

export interface SplitRow {
    id: string;
    name: string;
    percentage: number;
}

interface UseSplitFormParams {
    filteredSampleCount: Readable<number>;
    existingTagNames: Readable<string[]>;
}

// Percentages are integers in the UI, so an exact sum of 100 is required.
const REQUIRED_SUM = 100;

const DEFAULT_ROWS: SplitRow[] = [
    { id: 'train', name: 'train', percentage: 80 },
    { id: 'val', name: 'val', percentage: 10 },
    { id: 'test', name: 'test', percentage: 10 }
];

export function useSplitForm({ filteredSampleCount, existingTagNames }: UseSplitFormParams) {
    const rows = writable<SplitRow[]>(cloneDefaultRows());

    const percentageSum = derived(rows, ($rows) =>
        $rows.reduce((sum, row) => sum + (Number.isFinite(row.percentage) ? row.percentage : 0), 0)
    );

    const errorMessage = derived([rows, percentageSum], ([$rows, $sum]) =>
        computeErrorMessage($rows, $sum)
    );

    const isValid = derived(errorMessage, ($error) => $error === null);

    // Per-split counts previewed against the current filtered set, using the same
    // largest-remainder method as the backend so the numbers match the result.
    const previewCounts = derived([rows, filteredSampleCount], ([$rows, $count]) =>
        partitionCounts(
            $count,
            Object.fromEntries($rows.map((row) => [row.name, Math.max(row.percentage, 0)]))
        )
    );

    // Names of target splits that already exist as tags, so the caller can warn
    // that they will be cleared and reassigned.
    const overwrittenTagNames = derived([rows, existingTagNames], ([$rows, $existing]) => {
        const existingSet = new Set($existing);
        return $rows.map((row) => row.name).filter((name) => existingSet.has(name));
    });

    function addRow(): void {
        rows.update(($rows) => [...$rows, { id: crypto.randomUUID(), name: '', percentage: 0 }]);
    }

    function removeRow(id: string): void {
        rows.update(($rows) => $rows.filter((row) => row.id !== id));
    }

    function updateName(id: string, name: string): void {
        rows.update(($rows) => $rows.map((row) => (row.id === id ? { ...row, name } : row)));
    }

    function updatePercentage(id: string, percentage: number): void {
        const safe = Number.isFinite(percentage) ? percentage : 0;
        rows.update(($rows) =>
            $rows.map((row) => (row.id === id ? { ...row, percentage: safe } : row))
        );
    }

    function reset(): void {
        rows.set(cloneDefaultRows());
    }

    function getSizes(): Record<string, number> {
        return Object.fromEntries(get(rows).map((row) => [row.name.trim(), row.percentage]));
    }

    return {
        rows,
        percentageSum,
        errorMessage,
        isValid,
        previewCounts,
        overwrittenTagNames,
        addRow,
        removeRow,
        updateName,
        updatePercentage,
        reset,
        getSizes
    };
}

function cloneDefaultRows(): SplitRow[] {
    return DEFAULT_ROWS.map((row) => ({ ...row }));
}

function computeErrorMessage(rows: SplitRow[], sum: number): string | null {
    if (rows.length === 0) return 'Add at least one split.';

    const names = rows.map((row) => row.name.trim());
    if (names.some((name) => name.length === 0)) return 'Every split needs a name.';
    if (new Set(names).size !== names.length) return 'Split names must be unique.';
    if (rows.some((row) => row.percentage <= 0)) return 'Every percentage must be greater than 0.';
    if (sum !== REQUIRED_SUM) return `Percentages must sum to 100 (currently ${sum}).`;

    return null;
}
