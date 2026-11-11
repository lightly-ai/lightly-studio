interface LabelIdLookupParams {
    /** The classes of the dataset, loaded if needed. */
    getLabels: () => Promise<{ annotation_label_name: string; annotation_label_id?: string }[]>;
    /** Creates the class and returns its ID. */
    createLabel: (className: string) => Promise<string>;
}

/**
 * Returns the function that finds the ID of a class by name and creates the class when it is
 * missing. Boxes drawn while a class is created share that creation, so a sticky new class is
 * created once. A failed creation is forgotten, so the next box tries again.
 */
export const createLabelIdLookup = ({ getLabels, createLabel }: LabelIdLookupParams) => {
    const creations = new Map<string, Promise<string>>();

    return async (className: string): Promise<string> => {
        const labels = await getLabels();
        const existing = labels.find(
            (label) => label.annotation_label_name === className
        )?.annotation_label_id;
        if (existing) return existing;
        // No await between the lookup and the set, so a second box always finds the creation.
        let creation = creations.get(className);
        if (!creation) {
            creation = createLabel(className);
            creations.set(className, creation);
            creation.catch(() => creations.delete(className));
        }
        return creation;
    };
};
