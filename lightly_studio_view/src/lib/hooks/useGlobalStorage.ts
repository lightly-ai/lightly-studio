import { readDataset } from '$lib/api/lightly_studio_local/sdk.gen';
import type { GridType } from '$lib/types';
import { get, writable } from 'svelte/store';
import type { TagView as Tag } from '$lib/services/types';
import type { ClassifierInfo } from '$lib/services/types';
import { useSessionStorage } from './useSessionStorage/useSessionStorage';
import type { MetadataInfo } from '$lib/services/types';
import type { MetadataBounds } from '$lib/services/types';
import type { MetadataValues } from '$lib/services/types';
import { useReversibleActions } from './useReversibleActions';

const lastGridType = writable<GridType>('samples');
const selectedSampleIds = writable<Set<string>>(new Set());
const selectedSampleAnnotationCropIds = writable<Set<string>>(new Set());
const selectedAnnotationFilterIds = writable<Set<string>>(new Set());
const annotationsTotalCount = writable<number>(0);
const samplesTotalCount = writable<number>(0);
const hideAnnotations = writable<boolean>(false);
const textEmbedding = writable<TextEmbedding | undefined>(undefined);
const classifierSamples = writable<{
    positiveSampleIds: string[];
    negativeSampleIds: string[];
} | null>(null);

// Separate classifier selection variables to avoid interference with main grid
const classifierSelectedSampleIds = writable<Set<string>>(new Set());

const sampleSize = useSessionStorage<{
    width: number;
    height: number;
}>('lightlyStudio_sampleSize', {
    width: 200,
    height: 200
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

export type TextEmbedding = {
    embedding: number[];
    queryText: string;
};
interface ClassifierSamples {
    positiveSampleIds: string[];
    negativeSampleIds: string[];
}

const showPlot = writable<boolean>(false);

// Rewrite the hook to return values and methods
export const useGlobalStorage = () => {
    const reversibleActionsHook = useReversibleActions();
    const setTextEmbedding = (_textEmbedding: TextEmbedding) => {
        textEmbedding.set(_textEmbedding);
    };
    const setClassifierSamples = (samples: ClassifierSamples | null) => {
        classifierSamples.set(samples);
    };
    const clearClassifierSamples = () => {
        classifierSamples.set(null);
    };

    // Classifier-specific selection methods
    const toggleClassifierSampleSelection = (sampleId: string) => {
        classifierSelectedSampleIds.update((state) => {
            if (state.has(sampleId)) {
                state.delete(sampleId);
            } else {
                state.add(sampleId);
            }
            return state;
        });
    };

    const clearClassifierSelectedSamples = () => {
        classifierSelectedSampleIds.update((state) => {
            state.clear();
            return state;
        });
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

    return {
        tags,
        textEmbedding,
        setTextEmbedding,
        // Store values
        selectedSampleIds,
        selectedSampleAnnotationCropIds,
        selectedAnnotationFilterIds,
        annotationsTotalCount,
        samplesTotalCount,
        datasetVersions,
        hideAnnotations,
        classifiers,
        classifierSamples,
        setClassifierSamples,
        clearClassifierSamples,
        // Classifier-specific selection
        classifierSelectedSampleIds,
        toggleClassifierSampleSelection,
        clearClassifierSelectedSamples,

        // Metadata stores
        metadataBounds,
        metadataValues,
        metadataInfo,
        updateMetadataValues,
        updateMetadataBounds,
        updateMetadataInfo,

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
        toggleSampleSelection: (sampleId: string) => {
            selectedSampleIds.update((state) => {
                if (state.has(sampleId)) {
                    state.delete(sampleId);
                } else {
                    state.add(sampleId);
                }
                return state;
            });
        },
        clearSelectedSamples: () => {
            selectedSampleIds.update((state) => {
                state.clear();
                return state;
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

        setAnnotationsTotalCount: (count: number) => {
            annotationsTotalCount.set(count);
        },

        setSamplesTotalCount: (count: number) => {
            samplesTotalCount.set(count);
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

        // Reversible actions
        ...reversibleActionsHook
    };
};
