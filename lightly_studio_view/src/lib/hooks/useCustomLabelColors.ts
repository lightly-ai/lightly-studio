import type { AnnotationLabelTable } from '$lib/api/lightly_studio_local/types.gen';
import { createCustomColorStore } from '$lib/hooks/createCustomColorStore';

export type { CustomColor } from '$lib/hooks/createCustomColorStore';

// Singleton instance
const store = createCustomColorStore();

type CustomColor = NonNullable<ReturnType<typeof store.getSavedColor>>;

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

// The dataset of the last call, to notice a dataset switch.
let lastDatasetId: string | undefined;

// Skips classes of other datasets, so a stale class list after a dataset switch clears the map.
// A dataset switch also drops previews and saves in flight; a refetch of the same dataset keeps them.
export const setAnnotationClasses = (datasetId: string, classes: AnnotationClass[]): void => {
    if (datasetId !== lastDatasetId) {
        lastDatasetId = datasetId;
        store.reset();
    }
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
