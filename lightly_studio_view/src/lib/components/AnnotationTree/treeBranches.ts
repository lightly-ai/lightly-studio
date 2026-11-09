import type { UnannotatedImageCount } from '$lib/api/lightly_studio_local';
import type { GroupBy, TreeGroup } from './groupPairRows';
import { formatCount, summarizeRows, type PairKey, type PairRow, type TriState } from './pairRows';

export const NO_ANNOTATIONS = 'No annotations';

/** The "No annotations" row of one annotation source. */
export interface UnannotatedRow {
    sourceId: string;
    sourceName: string;
    ticked: boolean;
    count?: string;
}

/** A checkbox row under a group. Ticking it ticks its pairs and its "No annotations" sources. */
export interface TreeLeaf {
    id: string;
    label: string;
    ariaLabel: string;
    ticked: boolean;
    count?: string;
    pairs: PairKey[];
    unannotatedIds: string[];
}

export interface TreeBranch {
    id: string;
    name: string;
    isSource: boolean;
    count?: string;
    leaves: TreeLeaf[];
}

export const toPairKey = (row: PairRow): PairKey => ({
    collection_id: row.sourceId,
    annotation_label_id: row.labelId
});

/** The groups of the tree with their rows, "No annotations" rows included. */
export const buildTreeBranches = (
    groups: TreeGroup[],
    groupBy: GroupBy,
    unannotated: UnannotatedRow[]
): TreeBranch[] =>
    groupBy === 'source' ? bySource(groups, unannotated) : byClass(groups, unannotated);

export const buildUnannotatedRows = (
    sources: { id: string; name: string }[],
    counts: UnannotatedImageCount[],
    unticked: string[]
): UnannotatedRow[] =>
    sources.map((source) => {
        const count = counts.find((other) => other.annotation_collection_id === source.id);
        return {
            sourceId: source.id,
            sourceName: source.name,
            ticked: !unticked.includes(source.id),
            count: count && formatCount(count.current_count, count.total_count)
        };
    });

export const pairLeaf = (row: PairRow, label: string): TreeLeaf => ({
    id: `${row.sourceId}:${row.labelId}`,
    label,
    ariaLabel: `${row.className} in ${row.sourceName}`,
    ticked: row.ticked,
    count: formatCount(row.current, row.total),
    pairs: [toPairKey(row)],
    unannotatedIds: []
});

export const tickState = (leaves: TreeLeaf[]): TriState => {
    const ticked = leaves.filter((leaf) => leaf.ticked).length;
    if (ticked === leaves.length) return 'on';
    return ticked === 0 ? 'off' : 'partial';
};

export const leafTargets = (leaves: TreeLeaf[]) => ({
    pairs: leaves.flatMap((leaf) => leaf.pairs),
    unannotatedIds: leaves.flatMap((leaf) => leaf.unannotatedIds)
});

const unannotatedLeaf = (row: UnannotatedRow, label: string): TreeLeaf => ({
    id: `unannotated:${row.sourceId}`,
    label,
    ariaLabel: `${NO_ANNOTATIONS} in ${row.sourceName}`,
    ticked: row.ticked,
    count: row.count,
    pairs: [],
    unannotatedIds: [row.sourceId]
});

const summedCount = (rows: PairRow[]): string | undefined => {
    if (rows.length === 0) return undefined;
    const summary = summarizeRows(rows);
    return formatCount(summary.current, summary.total);
};

const bySource = (groups: TreeGroup[], unannotated: UnannotatedRow[]): TreeBranch[] =>
    groups.map((group) => {
        const none = unannotated.find((row) => row.sourceId === group.sourceId);
        return {
            id: group.id,
            name: group.name,
            isSource: true,
            count: summedCount(group.rows),
            leaves: [
                ...(none ? [unannotatedLeaf(none, NO_ANNOTATIONS)] : []),
                ...group.rows.map((row) => pairLeaf(row, row.className))
            ]
        };
    });

// "No annotations" counts images, so its group shows no sum.
const byClass = (groups: TreeGroup[], unannotated: UnannotatedRow[]): TreeBranch[] => {
    const classBranches = groups.map((group) => ({
        id: group.id,
        name: group.name,
        isSource: false,
        count: summedCount(group.rows),
        leaves: group.rows.map((row) => pairLeaf(row, row.sourceName))
    }));
    if (unannotated.length === 0) return classBranches;
    const noneBranch = {
        id: 'unannotated',
        name: NO_ANNOTATIONS,
        isSource: false,
        leaves: unannotated.map((row) => unannotatedLeaf(row, row.sourceName))
    };
    return [noneBranch, ...classBranches];
};
