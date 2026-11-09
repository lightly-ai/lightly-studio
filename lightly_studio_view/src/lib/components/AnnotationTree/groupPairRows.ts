import type { PairRow } from './pairRows';

export type GroupBy = 'source' | 'class';

export interface TreeGroup {
    id: string;
    name: string;
    /** Set when the group is an annotation source. */
    sourceId?: string;
    rows: PairRow[];
}

/**
 * Groups the rows by annotation source (every source, also without classes) or by annotation
 * class (classes of the same name across sources).
 */
export const groupPairRows = (
    rows: PairRow[],
    groupBy: GroupBy,
    sources: { id: string; name: string }[]
): TreeGroup[] => (groupBy === 'source' ? bySource(rows, sources) : byClass(rows));

const bySource = (rows: PairRow[], sources: { id: string; name: string }[]): TreeGroup[] =>
    sources.map((source) => ({
        id: source.id,
        name: source.name,
        sourceId: source.id,
        rows: rows.filter((row) => row.sourceId === source.id)
    }));

const byClass = (rows: PairRow[]): TreeGroup[] => {
    const groups = new Map<string, PairRow[]>();
    for (const row of rows) {
        const classRows = groups.get(row.className) ?? [];
        classRows.push(row);
        groups.set(row.className, classRows);
    }
    return [...groups.entries()]
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([name, classRows]) => ({ id: `class:${name}`, name, rows: classRows }));
};
