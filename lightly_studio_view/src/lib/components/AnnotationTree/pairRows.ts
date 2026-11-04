import type { AnnotationPairCount } from '$lib/api/lightly_studio_local';
import { formatInteger } from '$lib/utils';

export type PairKey = { collection_id: string; annotation_label_id: string };

export type TriState = 'on' | 'partial' | 'off';

/** One (annotation source, annotation class) pair of the tree, with its counts and state. */
export interface PairRow {
    sourceId: string;
    sourceName: string;
    labelId: string;
    className: string;
    current: number;
    total: number;
    ticked: boolean;
    visible: boolean;
}

/** The rows of the sources in source order, classes sorted by name within a source. */
export const buildPairRows = (
    sources: { id: string; name: string }[],
    counts: AnnotationPairCount[],
    unticked: PairKey[],
    hidden: PairKey[]
): PairRow[] =>
    sources.flatMap((source) =>
        counts
            .filter((count) => count.annotation_collection_id === source.id)
            .sort((a, b) => a.label_name.localeCompare(b.label_name))
            .map((count) => {
                const key = {
                    collection_id: source.id,
                    annotation_label_id: count.annotation_label_id
                };
                return {
                    sourceId: source.id,
                    sourceName: source.name,
                    labelId: count.annotation_label_id,
                    className: count.label_name,
                    current: count.current_count,
                    total: count.total_count,
                    ticked: !hasKey(unticked, key),
                    visible: !hasKey(hidden, key)
                };
            })
    );

/** Tri-state of the tick and the eye, ticked row count and summed counts of some rows. */
export const summarizeRows = (rows: PairRow[]) => {
    const ticked = rows.filter((row) => row.ticked).length;
    const visible = rows.filter((row) => row.visible).length;
    return {
        tick: toTriState(ticked, rows.length),
        eye: toTriState(visible, rows.length),
        ticked,
        current: rows.reduce((sum, row) => sum + row.current, 0),
        total: rows.reduce((sum, row) => sum + row.total, 0)
    };
};

/** "N" when nothing is filtered out, "a / b" otherwise. */
export const formatCount = (current: number, total: number): string =>
    current === total
        ? formatInteger(current)
        : `${formatInteger(current)} / ${formatInteger(total)}`;

const hasKey = (keys: PairKey[], key: PairKey): boolean =>
    keys.some(
        (other) =>
            other.collection_id === key.collection_id &&
            other.annotation_label_id === key.annotation_label_id
    );

// No rows reads as "on": it filters nothing out.
const toTriState = (count: number, length: number): TriState => {
    if (count === length) return 'on';
    return count === 0 ? 'off' : 'partial';
};
