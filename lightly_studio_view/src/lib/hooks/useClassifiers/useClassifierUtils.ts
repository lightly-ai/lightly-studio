import type { AnnotatedSamples, ClassifierExportType } from '$lib/services/types';
import { page } from '$app/state';
import { get, writable, type Readable } from 'svelte/store';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { triggerDownloadBlob } from '$lib/utils';
import {
    getNegativeSamples,
    saveClassifierToFile,
    loadClassifierFromBuffer,
    updateClassifiersAnnotations,
    trainClassifier as trainClassifierApi
} from '$lib/api/lightly_studio_local';

interface PrepareSamplesResponse {
    positiveSampleIds: string[];
    negativeSampleIds: string[];
}

interface UseClassifierUtilsReturn {
    error: Readable<Error | null>;
    isLoading: Readable<boolean>;
    classifiersSelected: Readable<Set<string>>;

    // Independent API functions
    saveClassifier: (classifierId: string, exportType: ClassifierExportType) => Promise<void>;
    loadClassifier: (event: Event, collectionId: string) => Promise<void>;
    updateAnnotations: (classifierId: string, annotations: AnnotatedSamples) => Promise<void>;
    trainClassifier: (classifierId: string) => Promise<void>;
    prepareSamples: () => Promise<PrepareSamplesResponse>;

    // Independent state management
    classifierSelectionToggle: (classifierId: string) => void;
    clearClassifiersSelected: () => void;
}

const { getSelectedSampleIds } = useGlobalStorage();
const classifiersSelected = writable<Set<string>>(new Set());

export function useClassifierUtils(): UseClassifierUtilsReturn {
    const error = writable<Error | null>(null);
    const isLoading = writable(false);

    const saveClassifier = async (classifierId: string, exportType: ClassifierExportType) => {
        try {
            error.set(null);
            const response = await saveClassifierToFile({
                path: { classifier_id: classifierId, export_type: exportType },
                parseAs: 'blob'
            });

            const contentDisposition = response.response.headers.get('content-disposition');
            const filenameMatch = contentDisposition?.match(/filename="(.+)"/);
            const filename = filenameMatch?.[1] ?? `classifier_${classifierId}.pkl`;

            if (!response.data) {
                error.set(new Error('No data received from the server'));
                return Promise.reject('No data received from the server');
            }

            // parseAs: 'blob' makes data a Blob at runtime, but the type is {} from OpenAPI spec
            triggerDownloadBlob(filename, response.data as unknown as Blob);
        } catch (err) {
            error.set(err as Error);
            throw err;
        }
    };

    const loadClassifier = async (event: Event, collectionId: string): Promise<void> => {
        error.set(null);
        const input = event.target as HTMLInputElement;
        const file = input.files?.[0];

        if (!file) {
            error.set(new Error('No file selected'));
            return;
        }

        try {
            await loadClassifierFromBuffer({
                query: { collection_id: collectionId },
                body: { file }
            });

            // Reset the input.
            input.value = '';
        } catch (err) {
            error.set(err as Error);
            throw err;
        }
    };

    const updateAnnotations = async (classifierId: string, annotations: AnnotatedSamples) => {
        try {
            error.set(null);
            await updateClassifiersAnnotations({
                path: { classifier_id: classifierId },
                body: annotations
            });
        } catch (err) {
            error.set(err as Error);
            throw err;
        }
    };

    const trainClassifier = async (classifierId: string) => {
        try {
            error.set(null);
            await trainClassifierApi({
                path: { classifier_id: classifierId }
            });
        } catch (err) {
            error.set(err as Error);
            throw err;
        }
    };

    async function prepareSamples(): Promise<PrepareSamplesResponse> {
        const collectionId = page.params.collection_id;
        const selectedSampleIds = getSelectedSampleIds(collectionId);
        const selectedIds = get(selectedSampleIds);
        const positives = Array.from(selectedIds);

        error.set(null);
        try {
            const response = await getNegativeSamples({
                body: {
                    collection_id: collectionId!.toString(),
                    positive_sample_ids: positives
                }
            });

            if (!response.data) {
                error.set(new Error('Failed to prepare samples'));
                return Promise.reject('Failed to prepare samples');
            }

            return {
                positiveSampleIds: positives,
                negativeSampleIds: response.data.negative_sample_ids
            };
        } catch (err) {
            error.set(err as Error);
            return Promise.reject(err as Error);
        }
    }

    const classifierSelectionToggle = (classifier_id: string) => {
        classifiersSelected.update((selected) => {
            if (selected.has(classifier_id)) {
                selected.delete(classifier_id);
            } else {
                selected.add(classifier_id);
            }
            return new Set([...selected]);
        });
    };

    const clearClassifiersSelected = () => {
        classifiersSelected.set(new Set());
    };

    return {
        error,
        isLoading,
        classifiersSelected,
        saveClassifier,
        loadClassifier,
        updateAnnotations,
        trainClassifier,
        prepareSamples,
        classifierSelectionToggle,
        clearClassifiersSelected
    };
}
