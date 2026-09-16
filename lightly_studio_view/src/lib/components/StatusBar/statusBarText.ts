import { formatInteger } from '$lib/utils';

interface StatusCountsParams {
    /** Items in the collection before any filter. */
    total: number;
    /** Items the current filters leave visible. */
    filtered: number;
    /** Plural noun for the item kind, e.g. "images". */
    itemType: string;
}

/** Left-hand status text: `Showing 128 images`, narrowed to `Showing 12 of 128 images`. */
export function formatShowingText({ total, filtered, itemType }: StatusCountsParams): string {
    if (!total) return '';
    if (filtered < total) {
        return `Showing ${formatInteger(filtered)} of ${formatInteger(total)} ${itemType}`;
    }
    return `Showing ${formatInteger(total)} ${itemType}`;
}

interface StatusContextParams {
    selectedCount: number;
    sourceCount: number;
    classCount: number;
}

/**
 * Right-hand status text.
 *
 * A live selection is the more urgent fact, so it replaces the class count rather than being
 * appended to an already long line.
 */
export function formatContextText({
    selectedCount,
    sourceCount,
    classCount
}: StatusContextParams): string {
    const sources = `${formatInteger(sourceCount)} annotation ${
        sourceCount === 1 ? 'source' : 'sources'
    }`;
    if (selectedCount > 0) {
        return `${formatInteger(selectedCount)} selected · ${sources}`;
    }
    if (classCount > 0) {
        return `${sources} · ${formatInteger(classCount)} ${classCount === 1 ? 'class' : 'classes'}`;
    }
    return sources;
}
