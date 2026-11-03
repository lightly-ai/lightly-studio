import type { PairRow } from './pairRows';

export type MatchRange = [start: number, end: number];

export type Matcher =
    | { kind: 'none' }
    | { kind: 'invalid' }
    | { kind: 'ok'; find: (text: string) => MatchRange | null };

/**
 * Matches names case-insensitively, as a substring or, with `useRegex`, as a regular
 * expression. An empty query matches nothing in particular; an invalid pattern is reported.
 */
export const createMatcher = (query: string, useRegex: boolean): Matcher => {
    const needle = query.trim();
    if (!needle) return { kind: 'none' };
    if (!useRegex) {
        const lower = needle.toLowerCase();
        return {
            kind: 'ok',
            find: (text) => {
                const start = text.toLowerCase().indexOf(lower);
                return start < 0 ? null : [start, start + lower.length];
            }
        };
    }
    try {
        const pattern = new RegExp(needle, 'i');
        return {
            kind: 'ok',
            find: (text) => {
                const match = pattern.exec(text);
                return match ? [match.index, match.index + match[0].length] : null;
            }
        };
    } catch {
        return { kind: 'invalid' };
    }
};

/**
 * The rows whose source name or class name matches. A source match keeps all its classes, a
 * class match keeps that class under each source. No query or an invalid one keeps all rows.
 */
export const matchRows = (rows: PairRow[], matcher: Matcher): PairRow[] => {
    if (matcher.kind !== 'ok') return rows;
    return rows.filter(
        (row) => matcher.find(row.sourceName) !== null || matcher.find(row.className) !== null
    );
};

/** Splits a text around a match range, for highlighting. */
export const splitAtRange = (text: string, range: MatchRange | null) =>
    range
        ? {
              before: text.slice(0, range[0]),
              match: text.slice(range[0], range[1]),
              after: text.slice(range[1])
          }
        : { before: text, match: '', after: '' };
