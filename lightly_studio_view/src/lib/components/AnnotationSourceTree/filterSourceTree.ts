import type { buildSourceTree } from './buildSourceTree';

type SourceTree = ReturnType<typeof buildSourceTree>;

const normalize = (text: string) => text.trim().toLowerCase();

/**
 * Keeps the classes whose name contains the query, case-insensitive, and drops the sources
 * left with none. An empty query keeps everything. Source state and counts stay as they were.
 */
export const filterSourceTree = (tree: SourceTree, query: string): SourceTree => {
    const needle = normalize(query);
    if (!needle) return tree;
    return tree
        .map((node) => ({
            ...node,
            classes: node.classes.filter((item) => item.label.toLowerCase().includes(needle))
        }))
        .filter((node) => node.classes.length > 0);
};

/** Splits a label into parts around the first match of the query, for highlighting. */
export const splitMatch = (label: string, query: string) => {
    const needle = normalize(query);
    const start = needle ? label.toLowerCase().indexOf(needle) : -1;
    if (start < 0) return { before: label, match: '', after: '' };
    const end = start + needle.length;
    return {
        before: label.slice(0, start),
        match: label.slice(start, end),
        after: label.slice(end)
    };
};
