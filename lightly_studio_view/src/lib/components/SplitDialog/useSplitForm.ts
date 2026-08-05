import { derived, get, writable, type Readable } from 'svelte/store';
import { partitionCounts } from './partitionCounts';

export interface SplitRow {
    id: string;
    name: string;
    parts: number;
}

export interface SplitPreview {
    percentage: number;
    count: number;
}

interface UseSplitFormParams {
    filteredSampleCount: Readable<number>;
}

// Splits are sized by relative parts (e.g. 8 : 1 : 1), so they never need to
// sum to any particular total.
const DEFAULT_ROWS: SplitRow[] = [
    { id: 'train', name: 'train', parts: 8 },
    { id: 'val', name: 'val', parts: 1 },
    { id: 'test', name: 'test', parts: 1 }
];

export function useSplitForm({ filteredSampleCount }: UseSplitFormParams) {
    const rows = writable<SplitRow[]>(cloneDefaultRows());

    const errorMessage = derived(rows, ($rows) => computeErrorMessage($rows));

    const isValid = derived(errorMessage, ($error) => $error === null);

    // Per-row percentage and sample count, keyed by row id so temporary empty or
    // duplicate names never collide. Counts use the same largest-remainder method
    // as the backend so the preview matches the actual result.
    const preview = derived([rows, filteredSampleCount], ([$rows, $count]) => {
        const partsById = Object.fromEntries($rows.map((row) => [row.id, Math.max(row.parts, 0)]));
        const partsSum = $rows.reduce((sum, row) => sum + Math.max(row.parts, 0), 0);
        const counts = partitionCounts($count, partsById);

        return Object.fromEntries(
            $rows.map((row): [string, SplitPreview] => [
                row.id,
                {
                    percentage:
                        partsSum > 0 ? Math.round((Math.max(row.parts, 0) / partsSum) * 100) : 0,
                    count: counts[row.id] ?? 0
                }
            ])
        );
    });

    function addRow(): void {
        rows.update(($rows) => [...$rows, { id: crypto.randomUUID(), name: '', parts: 1 }]);
    }

    function removeRow(id: string): void {
        rows.update(($rows) => $rows.filter((row) => row.id !== id));
    }

    function updateName(id: string, name: string): void {
        rows.update(($rows) => $rows.map((row) => (row.id === id ? { ...row, name } : row)));
    }

    function updateParts(id: string, parts: number): void {
        const safe = Number.isFinite(parts) ? parts : 0;
        rows.update(($rows) => $rows.map((row) => (row.id === id ? { ...row, parts: safe } : row)));
    }

    function reset(): void {
        rows.set(cloneDefaultRows());
    }

    function getSizes(): Record<string, number> {
        return Object.fromEntries(get(rows).map((row) => [row.name.trim(), row.parts]));
    }

    return {
        rows,
        errorMessage,
        isValid,
        preview,
        addRow,
        removeRow,
        updateName,
        updateParts,
        reset,
        getSizes
    };
}

function cloneDefaultRows(): SplitRow[] {
    return DEFAULT_ROWS.map((row) => ({ ...row }));
}

function computeErrorMessage(rows: SplitRow[]): string | null {
    if (rows.length === 0) return 'Add at least one split.';

    const names = rows.map((row) => row.name.trim());
    if (names.some((name) => name.length === 0)) return 'Every split needs a name.';
    if (new Set(names).size !== names.length) return 'Split names must be unique.';
    if (rows.some((row) => row.parts <= 0)) return 'Every split needs at least 1 part.';

    return null;
}
