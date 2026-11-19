import {
    EXCLUDED_BY_FILTERS_CATEGORY,
    INCLUDED_BY_FILTERS_CATEGORY,
    OTHER_BUCKET_CATEGORY
} from '../plotCategories';

// The backend re-ranks the label slots when the filters change, so a hidden class is stored
// by its label. The reserved rows get a fixed key instead.
const RESERVED_KEY_BY_CATEGORY = new Map<number, string>([
    [EXCLUDED_BY_FILTERS_CATEGORY, 'reserved:excluded'],
    [INCLUDED_BY_FILTERS_CATEGORY, 'reserved:included']
]);

// The Other bucket label lists its members, so it changes with the filters. The prefix
// matches _format_other_label in embedding_coloring/coloring_helpers.py.
const OTHER_BUCKET_KEY = 'other';
const OTHER_BUCKET_LABEL_PREFIX = 'Other (';

/**
 * Returns the key that identifies a legend row across legend changes, or undefined for a
 * class slot without a label.
 */
export function getLegendKey(category: number, label: string | undefined): string | undefined {
    const reservedKey = RESERVED_KEY_BY_CATEGORY.get(category);
    if (reservedKey !== undefined) return reservedKey;
    if (label === undefined) return undefined;
    const isOtherBucket =
        category === OTHER_BUCKET_CATEGORY && label.startsWith(OTHER_BUCKET_LABEL_PREFIX);
    return isOtherBucket ? OTHER_BUCKET_KEY : `label:${label}`;
}

/**
 * Maps hidden keys to the slots of the current legend. A key whose label is not in the
 * legend maps to no slot, and maps again once the label comes back. The reserved rows map
 * to their slots even when the legend does not list them.
 */
export function getHiddenCategories(
    hiddenKeys: ReadonlySet<string>,
    colorLegend: ReadonlyMap<number, string>
): Set<number> {
    const categories = new Set([...RESERVED_KEY_BY_CATEGORY.keys(), ...colorLegend.keys()]);
    return new Set(
        [...categories].filter((category) => {
            const key = getLegendKey(category, colorLegend.get(category));
            return key !== undefined && hiddenKeys.has(key);
        })
    );
}
