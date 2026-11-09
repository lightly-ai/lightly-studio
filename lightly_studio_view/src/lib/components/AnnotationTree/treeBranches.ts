import type { UnannotatedImageCount } from '$lib/api/lightly_studio_local';
import type { GroupBy, TreeGroup } from './groupPairRows';
import {
    formatCount,
    summarizeRows,
    toTriState,
    type PairKey,
    type PairRow,
    type TriState
} from './pairRows';

export const NO_ANNOTATIONS = 'No annotations';

/** The "No annotations" row of one annotation source. */
export interface UnannotatedRow {
    sourceId: string;
    sourceName: string;
    ticked: boolean;
    count?: string;
}

/** What the color mark of a row stands for. */
export interface TreeMark {
    kind: 'class' | 'source';
    name: string;
}

/** A checkbox row under a group. Ticking it ticks its pairs and its "No annotations" sources. */
export interface TreeLeaf {
    id: string;
    label: string;
    ariaLabel: string;
    ticked: boolean;
    /** The eye. "No annotations" rows have none. */
    visible?: boolean;
    count?: string;
    /** Absent on "No annotations" rows under a source, which have no color. */
    mark?: TreeMark;
    pairs: PairKey[];
    unannotatedIds: string[];
}

export interface TreeBranch {
    id: string;
    name: string;
    isSource: boolean;
    /** Absent on the "No annotations" group. */
    mark?: TreeMark;
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

export const pairLeaf = (row: PairRow, label: string, kind: TreeMark['kind']): TreeLeaf => ({
    id: `${row.sourceId}:${row.labelId}`,
    label,
    mark: { kind, name: label },
    ariaLabel: `${row.className} in ${row.sourceName}`,
    ticked: row.ticked,
    visible: row.visible,
    count: formatCount(row.current, row.total),
    pairs: [toPairKey(row)],
    unannotatedIds: []
});

export const tickState = (leaves: TreeLeaf[]): TriState =>
    toTriState(leaves.filter((leaf) => leaf.ticked).length, leaves.length);

/** The eye of the leaves that have one, or undefined when none has one. */
export const eyeState = (leaves: TreeLeaf[]): TriState | undefined => {
    const withEye = leaves.filter((leaf) => leaf.visible !== undefined);
    if (withEye.length === 0) return undefined;
    return toTriState(withEye.filter((leaf) => leaf.visible).length, withEye.length);
};

export const leafTargets = (leaves: TreeLeaf[]) => ({
    pairs: leaves.flatMap((leaf) => leaf.pairs),
    unannotatedIds: leaves.flatMap((leaf) => leaf.unannotatedIds)
});

const unannotatedLeaf = (row: UnannotatedRow, label: string, mark?: TreeMark): TreeLeaf => ({
    id: `unannotated:${row.sourceId}`,
    label,
    mark,
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
            mark: { kind: 'source', name: group.name },
            count: summedCount(group.rows),
            leaves: [
                ...(none ? [unannotatedLeaf(none, NO_ANNOTATIONS)] : []),
                ...group.rows.map((row) => pairLeaf(row, row.className, 'class'))
            ]
        };
    });

// "No annotations" counts images, so its group shows no sum.
const byClass = (groups: TreeGroup[], unannotated: UnannotatedRow[]): TreeBranch[] => {
    const classBranches = groups.map((group) => ({
        id: group.id,
        name: group.name,
        isSource: false,
        mark: { kind: 'class' as const, name: group.name },
        count: summedCount(group.rows),
        leaves: group.rows.map((row) => pairLeaf(row, row.sourceName, 'source'))
    }));
    if (unannotated.length === 0) return classBranches;
    const noneBranch = {
        id: 'unannotated',
        name: NO_ANNOTATIONS,
        isSource: false,
        leaves: unannotated.map((row) =>
            unannotatedLeaf(row, row.sourceName, { kind: 'source', name: row.sourceName })
        )
    };
    return [noneBranch, ...classBranches];
};
