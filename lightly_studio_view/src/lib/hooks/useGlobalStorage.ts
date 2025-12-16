import { readDataset } from '$lib/api/lightly_studio_local/sdk.gen';
import type { GridType } from '$lib/types';
import { derived, get, writable } from 'svelte/store';
import type { TagView as Tag } from '$lib/services/types';
import type { ClassifierInfo } from '$lib/services/types';
import { useSessionStorage } from './useSessionStorage/useSessionStorage';
import type { MetadataInfo } from '$lib/services/types';
import type { MetadataBounds } from '$lib/services/types';
import type { MetadataValues } from '$lib/services/types';
import { useReversibleActions } from './useReversibleActions';
import type { Point } from 'embedding-atlas/svelte';

const lastGridType = writable<GridType>('samples');
const selectedSampleIdsByDataset = writable<Record<string, Set<string>>>({});
const selectedSampleAnnotationCropIds = writable<Set<string>>(new Set());
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
// Cache dataset versions for more efficient image cache busting
const datasetVersions = writable<Record<string, string>>({});

const isEditingMode = writable<boolean>(false);
const setIsEditingMode = (isEditing: boolean) => {
    isEditingMode.set(isEditing);
};

const imageBrightness = writable<number>(1);
const imageContrast = writable<number>(1);

export type TextEmbedding = {
    embedding: number[];
    queryText: string;
};

const showPlot = writable<boolean>(false);
const rangeSelection = writable<Point[] | null>(null);

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

    // Helper function to get selected sample IDs for a specific dataset
    const getSelectedSampleIds = (dataset_id: string) => {
        return derived(selectedSampleIdsByDataset, ($selectedSampleIdsByDataset) => {
            return $selectedSampleIdsByDataset[dataset_id] ?? new Set<string>();
        });
    };

    return {
        tags,
        textEmbedding,
        setTextEmbedding,
        // Store values
        selectedSampleIdsByDataset,
        getSelectedSampleIds,
        selectedSampleAnnotationCropIds,
        selectedAnnotationFilterIds,
        filteredAnnotationCount,
        filteredSampleCount,
        datasetVersions,
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

        // Dataset version helpers for efficient image cache busting
        getDatasetVersion: async (datasetId: string): Promise<string> => {
            const versions = get(datasetVersions);

            if (versions[datasetId]) {
                return versions[datasetId];
            }

            const { data } = await readDataset({
                path: { dataset_id: datasetId }
            });
            if (data?.created_at) {
                const version = new Date(data.created_at).getTime().toString();
                datasetVersions.update((versions) => ({
                    ...versions,
                    [datasetId]: version
                }));
                return version;
            }

            return '';
        },

        // Individual sample selection methods
        toggleSampleSelection: (sampleId: string, dataset_id: string) => {
            selectedSampleIdsByDataset.update((selectedByDataset) => {
                const selected = selectedByDataset[dataset_id] ?? new Set<string>();
                if (selected.has(sampleId)) {
                    selected.delete(sampleId);
                } else {
                    selected.add(sampleId);
                }
                return {
                    ...selectedByDataset,
                    [dataset_id]: new Set([...selected])
                };
            });
        },
        clearSelectedSamples: (dataset_id: string) => {
            selectedSampleIdsByDataset.update((selectedByDataset) => {
                return {
                    ...selectedByDataset,
                    [dataset_id]: new Set()
                };
            });
        },

        // Individual sample annotation crop selection methods
        toggleSampleAnnotationCropSelection: (annotationId: string) => {
            selectedSampleAnnotationCropIds.update((state) => {
                if (state.has(annotationId)) {
                    state.delete(annotationId);
                } else {
                    state.add(annotationId);
                }
                return state;
            });
        },
        clearSelectedSampleAnnotationCrops: () => {
            selectedSampleAnnotationCropIds.update((state) => {
                state.clear();
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
        rangeSelection,
        setRangeSelection: (selection: Point[] | null) => {
            rangeSelection.set(selection);
        },

        imageBrightness,
        imageContrast,

        // Reversible actions
        ...reversibleActionsHook
    };
};
