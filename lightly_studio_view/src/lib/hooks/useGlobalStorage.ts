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
import type { CollectionView, SampleType, TagByFilterBody } from '$lib/api/lightly_studio_local';
import type { Point } from 'embedding-atlas/svelte';

const lastGridType = writable<GridType>('images');
const selectedSampleIdsByCollection = writable<Record<string, Set<string>>>({});
const selectedSampleAnnotationCropIds = writable<Record<string, Set<string>>>({});

/**
 * Snapshot of the filter behind a select-all. A non-`null` entry means the selection is still an
 * unmodified select-all, so it can be tagged by filter instead of materialized IDs; any manual
 * edit invalidates it. `size` lets the tag logic detect a selection that no longer matches.
 * `filter` is the by-filter tag endpoint's payload, so a snapshot can't hold a rejected filter.
 */
type SelectAllSnapshot = { filter: TagByFilterBody['filter']; size: number };

const selectAllSnapshotByCollection = writable<Record<string, SelectAllSnapshot | null>>({});
const selectAllAnnotationSnapshotByCollection = writable<Record<string, SelectAllSnapshot | null>>(
    {}
);

const invalidateSelectAllSnapshot = (collectionId: string) => {
    selectAllSnapshotByCollection.update((state) => ({ ...state, [collectionId]: null }));
};

const invalidateSelectAllAnnotationSnapshot = (collectionId: string) => {
    selectAllAnnotationSnapshotByCollection.update((state) => ({ ...state, [collectionId]: null }));
};
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

// Store the most recently selected annotation label.
const lastAnnotationLabel = useSessionStorage<Record<string, string>>(
    'lightlyStudio_last_annotation_label',
    {}
);

// Store the most recently selected annotation source.
const lastAnnotationSource = useSessionStorage<Record<string, string>>(
    'lightlyStudio_last_annotation_source',
    {}
);

// Store the most recently selected annotation brush size.
const lastAnnotationBrushSize = useSessionStorage<Record<string, number>>(
    'lightlyStudio_last_annotation_brush_size',
    {}
);

// Store tags grouped by collection_id
const tags = writable<Record<string, Tag[]>>({});
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

export type PanelType =
    | 'none'
    | 'embeddingPlot'
    | 'evaluationRuns'
    | 'queryEditor'
    | 'distribution';

const activePanel = writable<PanelType>('none');
const showEmbeddingPlot = derived(activePanel, ($p) => $p === 'embeddingPlot');
const showEvaluationRuns = derived(activePanel, ($p) => $p === 'evaluationRuns');

/** Toggle a panel on or off, leaving unrelated panels untouched. */
function togglePanel(current: PanelType, target: PanelType, show: boolean): PanelType {
    if (show) return target;
    return current === target ? 'none' : current;
}
const rangeSelectionBycollection = writable<Record<string, Point[] | null>>({});

// Rewrite the hook to return values and methods
export const useGlobalStorage = () => {
    const reversibleActionsHook = useReversibleActions();
    const setTextEmbedding = (_textEmbedding: TextEmbedding | undefined) => {
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

    const getRangeSelection = (collectionId: string) =>
        derived(
            rangeSelectionBycollection,
            ($rangeSelections) => $rangeSelections[collectionId] ?? null
        );

    // Select-all snapshot helpers (sample grid).
    const getSelectAllSnapshot = (collectionId: string) =>
        derived(selectAllSnapshotByCollection, ($snapshots) => $snapshots[collectionId] ?? null);
    const setSelectAllSnapshot = (collectionId: string, snapshot: SelectAllSnapshot) => {
        selectAllSnapshotByCollection.update((state) => ({ ...state, [collectionId]: snapshot }));
    };
    const clearSelectAllSnapshot = invalidateSelectAllSnapshot;

    // Select-all snapshot helpers (annotation grid).
    const getSelectAllAnnotationSnapshot = (collectionId: string) =>
        derived(
            selectAllAnnotationSnapshotByCollection,
            ($snapshots) => $snapshots[collectionId] ?? null
        );
    const setSelectAllAnnotationSnapshot = (collectionId: string, snapshot: SelectAllSnapshot) => {
        selectAllAnnotationSnapshotByCollection.update((state) => ({
            ...state,
            [collectionId]: snapshot
        }));
    };
    const clearSelectAllAnnotationSnapshot = invalidateSelectAllAnnotationSnapshot;

    return {
        tags,
        textEmbedding,
        setTextEmbedding,
        // Store values
        selectedSampleIdsByCollection,
        getSelectedSampleIds,
        selectedSampleAnnotationCropIds,

        // Select-all snapshots (sample + annotation grids)
        getSelectAllSnapshot,
        setSelectAllSnapshot,
        clearSelectAllSnapshot,
        getSelectAllAnnotationSnapshot,
        setSelectAllAnnotationSnapshot,
        clearSelectAllAnnotationSnapshot,

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
            invalidateSelectAllSnapshot(collection_id);
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
            invalidateSelectAllSnapshot(collection_id);
            selectedSampleIdsByCollection.update((selectedByCollection) => {
                return {
                    ...selectedByCollection,
                    [collection_id]: new Set()
                };
            });
        },

        setAllSelectedSampleIds: (collection_id: string, ids: Set<string>) => {
            selectedSampleIdsByCollection.update((selectedByCollection) => {
                return {
                    ...selectedByCollection,
                    [collection_id]: new Set([...ids])
                };
            });
        },

        // Individual sample annotation crop selection methods
        toggleSampleAnnotationCropSelection: (collectionId: string, annotationId: string) => {
            invalidateSelectAllAnnotationSnapshot(collectionId);
            selectedSampleAnnotationCropIds.update((state) => {
                const annotations = new Set(state[collectionId] ?? []);

                if (annotations.has(annotationId)) {
                    annotations.delete(annotationId);
                } else {
                    annotations.add(annotationId);
                }

                return {
                    ...state,
                    [collectionId]: annotations
                };
            });
        },
        clearSelectedSampleAnnotationCrops: (collectionId: string) => {
            invalidateSelectAllAnnotationSnapshot(collectionId);
            selectedSampleAnnotationCropIds.update((state) => {
                return {
                    ...state,
                    [collectionId]: new Set<string>()
                };
            });
        },
        setAllSelectedAnnotationCropIds: (collectionId: string, ids: Set<string>) => {
            selectedSampleAnnotationCropIds.update((state) => {
                return {
                    ...state,
                    [collectionId]: new Set([...ids])
                };
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
        activePanel,
        setActivePanel: (panel: PanelType) => activePanel.set(panel),
        showEmbeddingPlot,
        setShowEmbeddingPlot: (show: boolean) =>
            activePanel.update((p) => togglePanel(p, 'embeddingPlot', show)),
        showEvaluationRuns,
        setShowEvaluationRuns: (show: boolean) =>
            activePanel.update((p) => togglePanel(p, 'evaluationRuns', show)),
        getRangeSelection,
        setRangeSelectionForCollection: (collectionId: string, selection: Point[] | null) => {
            rangeSelectionBycollection.update((state) => ({
                ...state,
                [collectionId]: selection
            }));
        },

        imageBrightness,
        imageContrast,

        setCollection,
        retrieveParentCollection,
        collections,

        lastAnnotationLabel,
        updateLastAnnotationLabel: (collectionId: string, label: string) => {
            lastAnnotationLabel.update((value) => {
                value[collectionId] = label;
                return value;
            });
        },
        lastAnnotationSource,
        updateLastAnnotationSource: (collectionId: string, source: string) => {
            lastAnnotationSource.update((value) => {
                value[collectionId] = source;
                return value;
            });
        },
        lastAnnotationBrushSize,
        updateLastAnnotationBrushSize: (collectionId: string, size: number) => {
            lastAnnotationBrushSize.update((value) => {
                value[collectionId] = size;
                return value;
            });
        },
        // Reversible actions
        ...reversibleActionsHook
    };
};
