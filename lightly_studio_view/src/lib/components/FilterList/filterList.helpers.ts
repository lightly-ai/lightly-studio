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

/** The selection after "Select all": the selected items plus every visible item. */
export const selectAllVisible = (items: FilterListItem[], visible: FilterListItem[]): string[] => {
    const visibleIds = new Set(visible.map((item) => item.id));
    return items.filter((item) => item.selected || visibleIds.has(item.id)).map((item) => item.id);
};

/** Splits text into the parts before, inside and after the range. */
export const splitMatch = (
    text: string,
    range: { start: number; end: number } | null
): [string, string, string] =>
    range
        ? [text.slice(0, range.start), text.slice(range.start, range.end), text.slice(range.end)]
        : [text, '', ''];
