import type { AnnotationLabelTable } from '$lib/api/lightly_studio_local/types.gen';
import { createCustomColorStore, type CustomColor } from '$lib/hooks/createCustomColorStore';

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

// Class IDs of the current dataset by class name. Colors are keyed by name, the server by ID.
let currentDatasetId: string | undefined;
let classIdsByName = new Map<string, string>();

export const resetAnnotationClasses = (datasetId: string): void => {
    if (datasetId === currentDatasetId) return;
    currentDatasetId = datasetId;
    classIdsByName = new Map();
    store.reset();
};

export const setAnnotationClasses = (datasetId: string, classes: AnnotationClass[]): void => {
    if (datasetId !== currentDatasetId) return;
    classIdsByName = new Map();
    const savedColors: Record<string, CustomColor> = {};
    for (const c of classes) {
        if (c.dataset_id !== datasetId) continue;
        if (c.annotation_label_id) {
            classIdsByName.set(c.annotation_label_name, c.annotation_label_id);
        }
        if (c.color) {
            savedColors[c.annotation_label_name] = { color: c.color, alpha: c.alpha ?? 1 };
        }
    }
    // Also with no colors, so colors removed on the server go away.
    store.replaceSavedColors(savedColors);
};

export const getAnnotationClassId = (name: string): string | undefined => classIdsByName.get(name);
