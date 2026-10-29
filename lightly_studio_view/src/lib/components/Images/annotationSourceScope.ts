/**
 * Returns the selected annotation sources when they are a strict subset of the known
 * sources, so that the annotation filter only looks at those. Returns undefined when
 * every source or no source is selected: then there is nothing to restrict.
 */
export const getAnnotationSourceScope = (
    selectedIds: string[],
    knownIds: string[]
): string[] | undefined => {
    if (selectedIds.length === 0) return undefined;
    const allSelected = knownIds.every((id) => selectedIds.includes(id));
    return allSelected ? undefined : selectedIds;
};
