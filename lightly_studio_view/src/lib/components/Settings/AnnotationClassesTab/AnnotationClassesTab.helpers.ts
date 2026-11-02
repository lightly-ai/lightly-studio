interface AnnotationClass {
    annotation_label_name: string;
}

interface SearchAnnotationClassesReturn<T extends AnnotationClass> {
    sortedClasses: T[];
    visibleClasses: T[];
    exactMatch: T | undefined;
    canAdd: boolean;
    canAddWithEnter: boolean;
}

// Sorts the classes by name and filters them by the search text. The search text can
// also be added as a new class when no class has that exact name. Without a loaded
// class list, nothing can be added, because any name could already exist.
export const searchAnnotationClasses = <T extends AnnotationClass>(
    classes: T[] | undefined,
    searchText: string
): SearchAnnotationClassesReturn<T> => {
    const needle = searchText.toLowerCase();
    const sortedClasses = [...(classes ?? [])].sort((a, b) =>
        a.annotation_label_name.localeCompare(b.annotation_label_name)
    );
    const visibleClasses = sortedClasses.filter((c) =>
        c.annotation_label_name.toLowerCase().includes(needle)
    );
    const exactMatch = sortedClasses.find((c) => c.annotation_label_name.toLowerCase() === needle);
    const canAdd = classes !== undefined && searchText.length > 0 && !exactMatch;
    // Enter adds only when nothing matches, so a partial search like "bea" for "bear"
    // never adds a class by accident.
    const canAddWithEnter = canAdd && visibleClasses.length === 0;
    return { sortedClasses, visibleClasses, exactMatch, canAdd, canAddWithEnter };
};
