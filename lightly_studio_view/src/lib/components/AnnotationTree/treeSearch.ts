import type { PairRow } from './pairRows';
import type { GroupBy, TreeGroup } from './groupPairRows';

export type MatchRange = { start: number; end: number };

type Find = (text: string) => MatchRange | null;

/**
 * Matches text case-insensitively as a substring or, with `regex`, as a regular expression.
 * Returns null for an empty query. An invalid pattern matches nothing and sets `invalid`.
 */
export const buildMatcher = (
    query: string,
    regex: boolean
): { find: Find; invalid: boolean } | null => {
    const needle = query.trim();
    if (!needle) return null;
    if (!regex) {
        const lower = needle.toLowerCase();
        return {
            invalid: false,
            find: (text) => {
                const start = text.toLowerCase().indexOf(lower);
                return start < 0 ? null : { start, end: start + lower.length };
            }
        };
    }
    try {
        const pattern = new RegExp(needle, 'i');
        return {
            invalid: false,
            find: (text) => {
                const match = pattern.exec(text);
                return match ? { start: match.index, end: match.index + match[0].length } : null;
            }
        };
    } catch {
        return { invalid: true, find: () => null };
    }
};

/** The name a child row shows: its class under a source, its source under a class. */
export const childLabel = (row: PairRow, groupBy: GroupBy): string =>
    groupBy === 'source' ? row.className : row.sourceName;

/**
 * The groups that match. A group matching by name keeps all its rows, otherwise only the rows
 * whose child label matches are kept.
 */
export const filterGroups = (groups: TreeGroup[], find: Find, groupBy: GroupBy): TreeGroup[] =>
    groups.flatMap((group) => {
        if (find(group.name)) return [group];
        const rows = group.rows.filter((row) => find(childLabel(row, groupBy)));
        return rows.length > 0 ? [{ ...group, rows }] : [];
    });

/** The rows the "All annotations" toggles act on. */
export const rowsInScope = (groups: TreeGroup[]): PairRow[] =>
    groups.flatMap((group) => group.rows);
