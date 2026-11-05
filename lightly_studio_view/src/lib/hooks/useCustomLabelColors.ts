import type { AnnotationLabelTable } from '$lib/api/lightly_studio_local/types.gen';
import { createCustomColorStore } from '$lib/hooks/createCustomColorStore';

export type { CustomColor } from '$lib/hooks/createCustomColorStore';

// Singleton instance
const store = createCustomColorStore();

export const useCustomLabelColors = () => ({
    ...store,
    customLabelColorsStore: store.customColorsStore
});

type AnnotationClass = Pick<
    AnnotationLabelTable,
    'annotation_label_id' | 'annotation_label_name' | 'dataset_id' | 'color' | 'alpha'
>;

// Class IDs of the dataset by class name. Colors are keyed by name, the server by ID.
let classIdsByName = new Map<string, string>();

// Skips classes of other datasets, so a stale class list after a dataset switch clears the map.
export const setAnnotationClasses = (datasetId: string, classes: AnnotationClass[]): void => {
    classIdsByName = new Map();
    for (const c of classes) {
        if (c.dataset_id === datasetId && c.annotation_label_id) {
            classIdsByName.set(c.annotation_label_name, c.annotation_label_id);
        }
    }
};

export const getAnnotationClassId = (name: string): string | undefined => classIdsByName.get(name);
