import type { SourceLabelCount, SourceLabelPair } from '$lib/api/lightly_studio_local';
import { formatInteger } from '$lib/utils';
import { getSourceState } from '$lib/hooks/useAnnotationPairFilter/useAnnotationPairFilter';

export const formatCount = (current: number, total: number) =>
    `${formatInteger(current)} of ${formatInteger(total)}`;

/**
 * One row per annotation source, with its annotation classes as children.
 *
 * The parent count adds up its class counts, so an image with two classes of the source
 * counts twice.
 */
export const buildSourceTree = (
    sources: { id: string; name: string }[],
    counts: SourceLabelCount[],
    pairs: SourceLabelPair[]
) =>
    sources.map((source) => {
        const rows = counts
            .filter((count) => count.annotation_collection_id === source.id)
            .sort((a, b) => a.label_name.localeCompare(b.label_name));
        const labelIds = rows.map((row) => row.annotation_label_id);
        const classes = rows.map((row) => ({
            id: row.annotation_label_id,
            label: row.label_name,
            ariaLabel: source.name ? `${row.label_name} in ${source.name}` : undefined,
            selected: pairs.some(
                (pair) =>
                    pair.collection_id === source.id &&
                    pair.annotation_label_id === row.annotation_label_id
            ),
            count: formatCount(row.current_count, row.total_count)
        }));
        const current = rows.reduce((sum, row) => sum + row.current_count, 0);
        const total = rows.reduce((sum, row) => sum + row.total_count, 0);
        return {
            id: source.id,
            name: source.name,
            labelIds,
            classes,
            state: getSourceState(pairs, source.id, labelIds),
            count: rows.length > 0 ? formatCount(current, total) : undefined
        };
    });
