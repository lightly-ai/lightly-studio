import type { SourceLabelCount } from '$lib/api/lightly_studio_local';
import {
    isPairTicked,
    type NamedPair
} from '$lib/hooks/useAnnotationPairFilter/pairFilter.helpers';
import { formatInteger } from '$lib/utils';

/** One (annotation source, annotation class) pair of the tree, with its counts and tick. */
export interface PairRow {
    sourceId: string;
    sourceName: string;
    labelId: string;
    className: string;
    current: number;
    total: number;
    ticked: boolean;
}

export type TickState = 'checked' | 'partial' | 'unchecked';

/** "N" when nothing is filtered out, "a / b" otherwise. */
export const formatCount = (current: number, total: number) =>
    current === total
        ? formatInteger(current)
        : `${formatInteger(current)} / ${formatInteger(total)}`;

export const toNamedPair = (row: PairRow): NamedPair => ({
    collection_id: row.sourceId,
    annotation_label_id: row.labelId,
    label_name: row.className
});

/** The pairs of the sources in source order, classes sorted by name within a source. */
export const buildPairRows = (
    sources: { id: string; name: string }[],
    counts: SourceLabelCount[],
    unticked: NamedPair[]
): PairRow[] =>
    sources.flatMap((source) =>
        counts
            .filter((count) => count.annotation_collection_id === source.id)
            .sort((a, b) => a.label_name.localeCompare(b.label_name))
            .map((count) => ({
                sourceId: source.id,
                sourceName: source.name,
                labelId: count.annotation_label_id,
                className: count.label_name,
                current: count.current_count,
                total: count.total_count,
                ticked: isPairTicked(unticked, {
                    collection_id: source.id,
                    annotation_label_id: count.annotation_label_id
                })
            }))
    );

/** Tick state, ticked count and summed count of some rows. */
export const summarizeRows = (rows: PairRow[]) => {
    const ticked = rows.filter((row) => row.ticked).length;
    // A source without classes reads as ticked: it hides nothing.
    const state: TickState =
        ticked === rows.length ? 'checked' : ticked === 0 ? 'unchecked' : 'partial';
    const current = rows.reduce((sum, row) => sum + row.current, 0);
    const total = rows.reduce((sum, row) => sum + row.total, 0);
    return { state, ticked, count: rows.length > 0 ? formatCount(current, total) : undefined };
};
