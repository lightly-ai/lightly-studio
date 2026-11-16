export interface FilterListItem {
    id: string;
    label: string;
    /** Whether the item is part of the applied selection. */
    selected: boolean;
    /** Text shown at the end of the row, e.g. "3 of 8". */
    count?: string;
    /** Accessible name of the checkbox. Defaults to the label. */
    ariaLabel?: string;
}

/** Whether the item label contains the search text, ignoring case. */
export const matchesSearch = (item: FilterListItem, search: string): boolean =>
    item.label.toLowerCase().includes(search.trim().toLowerCase());

/** The selection after "Select all": the selected items plus every matching item. */
export const selectAllMatching = (
    items: FilterListItem[],
    matching: FilterListItem[]
): string[] => {
    const matchingIds = new Set(matching.map((item) => item.id));
    return items.filter((item) => item.selected || matchingIds.has(item.id)).map((item) => item.id);
};

/** Character range of the first case-insensitive match of the search in the label. */
export const highlightRange = (
    label: string,
    search: string
): { start: number; end: number } | null => {
    const query = search.trim().toLowerCase();
    const start = query ? label.toLowerCase().indexOf(query) : -1;
    return start === -1 ? null : { start, end: start + query.length };
};

/** Splits text into the parts before, inside and after the range. */
export const splitMatch = (
    text: string,
    range: { start: number; end: number } | null
): [string, string, string] =>
    range
        ? [text.slice(0, range.start), text.slice(range.start, range.end), text.slice(range.end)]
        : [text, '', ''];
