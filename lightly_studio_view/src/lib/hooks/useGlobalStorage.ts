import { readCollection } from '$lib/api/lightly_studio_local/sdk.gen';
import type { GridType } from '$lib/types';
import { derived, get, writable } from 'svelte/store';
import type { TagView as Tag } from '$lib/services/types';
import type { ClassifierInfo } from '$lib/services/types';
import { useSessionStorage } from './useSessionStorage/useSessionStorage';
import type { MetadataInfo } from '$lib/services/types';
import type { MetadataBounds } from '$lib/services/types';
import type { MetadataValues } from '$lib/services/types';
import { useReversibleActions } from './useReversibleActions';
import type { CollectionView, SampleType } from '$lib/api/lightly_studio_local';

const lastGridType = writable<GridType>('samples');
const selectedSampleIdsByCollection = writable<Record<string, Set<string>>>({});
const selectedSampleAnnotationCropIds = writable<Record<string, Set<string>>>({});
const selectedAnnotationFilterIds = writable<Set<string>>(new Set());
const filteredAnnotationCount = writable<number>(0);
const filteredSampleCount = writable<number>(0);
const filteredFramesCount = writable<number>(0);
const hideAnnotations = writable<boolean>(false);
const textEmbedding = writable<TextEmbedding | undefined>(undefined);

const sampleSize = useSessionStorage<{
    width: number;
    height: number;
}>('lightlyStudio_sampleSize', {
    width: 6,
    height: 6
});

// Metadata stores
const metadataBounds = useSessionStorage<MetadataBounds>('lightlyStudio_metadata_bounds', {});
const metadataValues = useSessionStorage<MetadataValues>('lightlyStudio_metadata_values', {});
const metadataInfo = useSessionStorage<MetadataInfo[]>('lightlyStudio_metadata_info', []);

const tags = writable<Tag[] | undefined>(undefined);
const classifiers = writable<ClassifierInfo[]>([]);
// Cache collection versions for more efficient image cache busting
const collectionVersions = writable<Record<string, string>>({});

const isEditingMode = writable<boolean>(false);
const setIsEditingMode = (isEditing: boolean) => {
    isEditingMode.set(isEditing);
};

const imageBrightness = writable<number>(1);
const imageContrast = writable<number>(1);

const collections = writable<
    Record<
        string,
        {
            sampleType: SampleType;
            parentCollectionId: string | undefined | null;
            collectionId: string;
        }
    >
>({});

export type TextEmbedding = {
    embedding: number[];
    queryText: string;
};

const showPlot = writable<boolean>(false);

// Rewrite the hook to return values and methods
export const useGlobalStorage = () => {
    const reversibleActionsHook = useReversibleActions();
    const setTextEmbedding = (_textEmbedding: TextEmbedding) => {
        textEmbedding.set(_textEmbedding);
    };

    // Metadata update methods
    const updateMetadataValues = (values: MetadataValues) => {
        metadataValues.set(values);
    };
    const updateMetadataBounds = (bounds: MetadataBounds) => {
        metadataBounds.set(bounds);
    };
    const updateMetadataInfo = (info: MetadataInfo[]) => {
        metadataInfo.set(info);
    };
    const setCollection = (collection: CollectionView) => {
        collections.update((prev) => ({
            ...prev,
            [collection.collection_id]: {
                sampleType: collection.sample_type,
                parentCollectionId: collection.parent_collection_id,
                collectionId: collection.collection_id
            }
        }));
    };

    const retrieveParentCollection = (
        collectionsRecord: Record<
            string,
            {
                sampleType: SampleType;
                parentCollectionId: string | null | undefined;
                collectionId: string;
            }
        >,
        collectionId: string
    ) => {
        const collection = collectionsRecord[collectionId];
        if (!collection?.parentCollectionId) return null;

        return collectionsRecord[collection.parentCollectionId];
    };

    // Helper function to get selected sample IDs for a specific collection
    const getSelectedSampleIds = (collection_id: string) => {
        return derived(selectedSampleIdsByCollection, ($selectedSampleIdsByCollection) => {
            return $selectedSampleIdsByCollection[collection_id] ?? new Set<string>();
        });
    };

    return {
        tags,
        textEmbedding,
        setTextEmbedding,
        // Store values
        selectedSampleIdsByCollection,
        getSelectedSampleIds,
        selectedSampleAnnotationCropIds,
        selectedAnnotationFilterIds,
        filteredAnnotationCount,
        filteredSampleCount,
        collectionVersions,
        hideAnnotations,
        classifiers,

        // Metadata stores
        metadataBounds,
        metadataValues,
        metadataInfo,
        updateMetadataValues,
        updateMetadataBounds,
        updateMetadataInfo,
        filteredFramesCount,
        // Annotation visibility control
        setHideAnnotations: (hide: boolean) => {
            hideAnnotations.set(hide);
        },

        // Collection version helpers for efficient image cache busting
        getCollectionVersion: async (collectionId: string): Promise<string> => {
            const versions = get(collectionVersions);

            if (versions[collectionId]) {
                return versions[collectionId];
            }

            const { data } = await readCollection({
                path: { collection_id: collectionId }
            });
            if (data?.created_at) {
                const version = new Date(data.created_at).getTime().toString();
                collectionVersions.update((versions) => ({
                    ...versions,
                    [collectionId]: version
                }));
                return version;
            }

            return '';
        },

        // Individual sample selection methods
        toggleSampleSelection: (sampleId: string, collection_id: string) => {
            selectedSampleIdsByCollection.update((selectedByCollection) => {
                const selected = selectedByCollection[collection_id] ?? new Set<string>();
                if (selected.has(sampleId)) {
                    selected.delete(sampleId);
                } else {
                    selected.add(sampleId);
                }
                return {
                    ...selectedByCollection,
                    [collection_id]: new Set([...selected])
                };
            });
        },
        clearSelectedSamples: (collection_id: string) => {
            selectedSampleIdsByCollection.update((selectedByCollection) => {
                return {
                    ...selectedByCollection,
                    [collection_id]: new Set()
                };
            });
        },

        // Individual sample annotation crop selection methods
        toggleSampleAnnotationCropSelection: (collectionId: string, annotationId: string) => {
            selectedSampleAnnotationCropIds.update((state) => {
                const annotations = state[collectionId] ?? new Set();

                if (annotations.has(annotationId)) {
                    annotations.delete(annotationId);
                } else {
                    annotations.add(annotationId);
                }

                state[collectionId] = annotations;
                return state;
            });
        },
        clearSelectedSampleAnnotationCrops: (collectionId: string) => {
            selectedSampleAnnotationCropIds.update((state) => {
                const annotations = state[collectionId];
                if (annotations) {
                    annotations.clear();
                    state[collectionId] = annotations;
                }

                return state;
            });
        },

        // remember the last grid type used even after multiple consecutive navigations
        lastGridType,
        setLastGridType: (gridType: GridType) => {
            lastGridType.set(gridType);
        },

        // remember active label/annotation filters
        setSelectedAnnotationFilterIds: (annotationFilterId: string) => {
            selectedAnnotationFilterIds.update((state) => {
                if (state.has(annotationFilterId)) {
                    state.delete(annotationFilterId);
                } else {
                    state.add(annotationFilterId);
                }
                return state;
            });
        },
        clearSelectedAnnotationFilterIds: () => {
            selectedAnnotationFilterIds.update((state) => {
                state.clear();
                return state;
            });
        },

        setfilteredAnnotationCount: (count: number) => {
            filteredAnnotationCount.set(count);
        },

        setfilteredSampleCount: (count: number) => {
            filteredSampleCount.set(count);
        },
        setfilteredFramesCount: (count: number) => {
            filteredFramesCount.set(count);
        },

        // Sample size
        sampleSize,
        // We have always square samples, so we only need to update one dimension
        updateSampleSize: (sideWidth: number) => {
            sampleSize.set({
                width: sideWidth,
                height: sideWidth
            });
        },

        isEditingMode,
        setIsEditingMode,
        showPlot,
        setShowPlot: (show: boolean) => {
            showPlot.set(show);
        },

        imageBrightness,
        imageContrast,

        setCollection,
        retrieveParentCollection,
        collections,

        // Reversible actions
        ...reversibleActionsHook
    };
};
