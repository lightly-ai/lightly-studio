import { writable } from 'svelte/store';

export const DEFAULT_COLLECTION_COLORS = [
    '#3b82f6', // blue
    '#ef4444', // red
    '#22c55e', // green
    '#f59e0b', // amber
    '#8b5cf6', // violet
    '#ec4899', // pink
    '#14b8a6', // teal
    '#f97316', // orange
    '#6366f1', // indigo
    '#84cc16' // lime
];

const selectedCollectionIds = writable<string[]>([]);
const collectionIdToName = writable<Record<string, string>>({});
const collectionIdToColor = writable<Record<string, string>>({});

export const useAnnotationCollectionsFilter = () => {
    return {
        selectedCollectionIds,
        setSelectedCollectionIds: (ids: string[]) => selectedCollectionIds.set(ids),
        collectionIdToName,
        setCollectionIdToName: (map: Record<string, string>) => collectionIdToName.set(map),
        collectionIdToColor,
        setCollectionIdToColor: (map: Record<string, string>) => collectionIdToColor.set(map),
        setCollectionColor: (id: string, color: string) =>
            collectionIdToColor.update((m) => ({ ...m, [id]: color }))
    };
};
