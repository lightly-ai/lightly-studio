interface AnnotationSource {
    name: string;
}

// Sorts the sources by name and filters them by the search text. Enter adds the search
// text as a new source only when no source matches, as on the annotation classes tab.
export const searchAnnotationSources = <T extends AnnotationSource>(
    sources: T[] | undefined,
    searchText: string
) => {
    const needle = searchText.toLowerCase();
    const sortedSources = [...(sources ?? [])].sort((a, b) => a.name.localeCompare(b.name));
    const visibleSources = sortedSources.filter((s) => s.name.toLowerCase().includes(needle));
    const exactMatch = sortedSources.find((s) => s.name === searchText);
    const canAdd = sources !== undefined && searchText.length > 0 && !exactMatch;
    const canAddWithEnter = canAdd && visibleSources.length === 0;
    return { sortedSources, visibleSources, exactMatch, canAdd, canAddWithEnter };
};
