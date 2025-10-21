import type {
    ClassifierInfo,
    AnnotatedSamples,
    RefineMode,
    ClassifierExportType
} from '$lib/services/types';
import { page } from '$app/state';
import { get, readonly, type Readable, writable } from 'svelte/store';
import client from '$lib/services/dataset';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { useCreateClassifiersPanel } from '$lib/hooks/useClassifiers/useCreateClassifiersPanel';
import { useRefineClassifiersPanel } from '$lib/hooks/useClassifiers/useRefineClassifiersPanel';
import { toast } from 'svelte-sonner';
import type { components } from '$lib/schema';
import { routeHelpers } from '$lib/routes';
import { goto } from '$app/navigation';
import { sampleHistory } from '$lib/api/lightly_studio_local';

// Import the utility functions
import { useClassifierUtils } from './useClassifierUtils';

type CreateClassifierRequest = components['schemas']['CreateClassifierRequest'];
type CreateClassifierResponse = components['schemas']['CreateClassifierResponse'];

interface PrepareSamplesResponse {
    positiveSampleIds: string[];
    negativeSampleIds: string[];
}

interface UseClassifiersReturn {
    classifiers: Readable<ClassifierInfo[]>;
    classifiersSelected: Readable<Set<string>>;
    isLoading: Readable<boolean>;
    error: Readable<Error | null>;

    clearClassifiersSelected: () => void;
    loadClassifiers: () => void;
    createClassifier: (request: CreateClassifierRequest) => Promise<CreateClassifierResponse>;
    classifierSelectionToggle: (classifierId: string) => void;
    apply: () => Promise<void>;
    saveClassifier: (classifierId: string, exportType: ClassifierExportType) => Promise<void>;
    trainClassifier: (classifierId: string) => Promise<void>;
    updateAnnotations: (classifierId: string, annotations: AnnotatedSamples) => Promise<void>;
    commitTempClassifier: (classifierId: string, datasetId: string) => Promise<void>;
    getSamplesToRefine: (
        classifierId: string,
        datasetId: string,
        classifierClasses: string[]
    ) => Promise<void>;
    prepareSamples: () => Promise<PrepareSamplesResponse>;
    loadClassifier: (event: Event) => Promise<void>;
    startCreateClassifier: (event: Event) => Promise<void>;
    startRefinment: (
        mode: RefineMode,
        classifierId: string,
        classifierName: string,
        classifierClasses: string[],
        datasetId: string
    ) => void;
    refineClassifier: (
        classifierID: string,
        datasetId: string,
        classifierClasses: string[]
    ) => void;
    showClassifierTrainingSamples: (
        classifierID: string,
        datasetId: string,
        classifierClasses: string[],
        toggle: boolean
    ) => void;
}

const {
    classifiers: classifiersData,
    selectedSampleIds,
    classifierSamples,
    setClassifierSamples,
    toggleSampleSelection,
    clearSelectedSamples
} = useGlobalStorage();

export function useClassifiers(): UseClassifiersReturn {
    // Use the utility functions
    const utils = useClassifierUtils();
    const error = writable<Error | null>(null);
    const isLoading = writable(false);
    const isLoaded = writable(false);
    const { openRefineClassifiersPanel, closeRefineClassifiersPanel } = useRefineClassifiersPanel();
    const { toggleCreateClassifiersPanel, closeCreateClassifiersPanel } =
        useCreateClassifiersPanel();

    const loadClassifiers = () => {
        if (get(isLoading)) return;
        error.set(null);
        isLoading.set(true);
        client
            .GET('/api/classifiers/get_all_classifiers')
            .then((response) => {
                if (response.data?.classifiers) {
                    // Extract just the classifiers array from the response.
                    classifiersData.set(response.data.classifiers);
                } else {
                    classifiersData.set([]); // Set empty array if no data.
                }
            })
            .catch((err) => {
                error.set(err as Error);
            })
            .finally(() => {
                isLoading.set(false);
            });
    };

    // Initialize classifiers on hook creation
    if (!get(isLoaded)) {
        loadClassifiers();
        isLoaded.set(true);
    }

    async function startCreateClassifier() {
        error.set(null);
        const datasetId = page.params.dataset_id;
        try {
            const result = await utils.prepareSamples();

            setClassifierSamples({
                positiveSampleIds: result.positiveSampleIds,
                negativeSampleIds: result.negativeSampleIds
            });
            toggleCreateClassifiersPanel();
            goto(routeHelpers.toClassifiers(datasetId));
            error.set(null);
        } catch (err) {
            error.set(err as Error);
        }
    }

    async function createClassifier(
        request: CreateClassifierRequest
    ): Promise<CreateClassifierResponse> {
        try {
            error.set(null);
            if (!request.dataset_id) {
                throw new Error('Dataset ID is required');
            }

            const response = await client.POST('/api/classifiers/create', {
                body: {
                    name: request.name,
                    class_list: request.class_list,
                    dataset_id: request.dataset_id.toString()
                }
            });

            if (!response.data) {
                error.set(Error('Failed to create classifier.'));
                return Promise.reject('Failed to create classifier.');
            }
            const currentClassifierSamples = get(classifierSamples);
            const allSampleIds = currentClassifierSamples
                ? [
                      ...currentClassifierSamples.positiveSampleIds,
                      ...currentClassifierSamples.negativeSampleIds
                  ]
                : [];

            // Convert selectedSampleIds Set to array.
            const currentSelectedIds = get(selectedSampleIds);
            const positiveIds = Array.from(currentSelectedIds);

            // Calculate negative IDs by filtering allSampleIds.
            const negativeIds = allSampleIds.filter((id) => !currentSelectedIds.has(id));

            // Create the annotated samples object.
            const annotatedSamples = {
                annotations: {
                    positive: positiveIds,
                    negative: negativeIds
                }
            };
            await utils.updateAnnotations(response.data.classifier_id, annotatedSamples);
            await utils.trainClassifier(response.data.classifier_id);

            await getSamplesToRefine(
                response.data.classifier_id,
                request.dataset_id.toString(),
                request.class_list
            );
            // Open the Refine Classifiers panel with the new classifier.
            openRefineClassifiersPanel(
                'temp',
                response.data.classifier_id,
                response.data.name,
                request.class_list
            );
            closeCreateClassifiersPanel();
            return response.data;
        } catch (e) {
            error.set(e as Error);
            return Promise.reject(e as Error);
        }
    }

    const apply = async () => {
        try {
            isLoading.set(true);
            error.set(null);

            const selectedClassifiers = Array.from(get(utils.classifiersSelected));

            // Run classifiers sequentially
            for (const classifier_id of selectedClassifiers) {
                // Get classifier info for toast message
                const classifier = get(classifiersData).find(
                    (c) => c.classifier_id === classifier_id
                );
                if (classifier) {
                    // Generate labels with pattern classifier_name_class
                    const generatedLabels =
                        classifier.class_list?.map(
                            (class_name) => `${classifier.classifier_name}_${class_name}`
                        ) || [];

                    await client.POST(
                        '/api/classifiers/{classifier_id}/run_on_dataset/{dataset_id}',
                        {
                            params: {
                                path: {
                                    classifier_id: classifier_id,
                                    dataset_id: page.params.dataset_id
                                }
                            }
                        }
                    );

                    // Show toast for each classifier run
                    toast.success(
                        `Classifier "${classifier.classifier_name}" completed successfully. ` +
                            `New labels added: ${generatedLabels.join(', ')}. ` +
                            `Annotations have been added to your dataset.`,
                        {
                            duration: 10000, // 10 seconds
                            closeButton: true
                        }
                    );
                }
            }

            isLoading.set(false);
        } catch (err) {
            isLoading.set(false);
            error.set(err as Error);
            toast.error('Failed to run classifiers: ' + (err as Error).message, {
                duration: 10000, // 10 seconds
                closeButton: true
            });
        }
    };

    const commitTempClassifier = async (classifierId: string, datasetId: string) => {
        try {
            error.set(null);
            await client.POST('/api/classifiers/{classifier_id}/commit_temp_classifier', {
                params: {
                    path: {
                        classifier_id: classifierId
                    }
                }
            });
            // Refresh classifiers list.
            loadClassifiers();
        } catch (err) {
            error.set(err as Error);
            return;
        }

        clearSelectedSamples();
        closeRefineClassifiersPanel();
        goto(routeHelpers.toSamples(datasetId));
    };

    const getSamplesToRefine = async (
        classifierId: string,
        datasetId: string,
        classes: string[]
    ) => {
        try {
            error.set(null);
            const response = await client.GET(
                '/api/classifiers/{classifier_id}/samples_to_refine',
                {
                    params: {
                        path: {
                            classifier_id: classifierId
                        },
                        query: {
                            dataset_id: datasetId
                        }
                    }
                }
            );

            if (!response.data?.samples) {
                error.set(new Error('Failed to get samples for refinement.'));
                return;
            }

            const samples = response.data.samples;
            const keys = Object.keys(samples);

            if (keys.length !== 2) {
                error.set(new Error('Invalid samples response structure'));
                return;
            }
            // Check if all classes exist in keys
            if (!classes.every((className) => keys.includes(className))) {
                error.set(new Error(`Invalid class names. Expected classes: ${keys.join(', ')}`));
                return;
            }
            // Create the prepared samples object
            const prepared = {
                positiveSampleIds: samples[classes[0]] || [],
                negativeSampleIds: samples[classes[1]] || []
            };

            // Update the selection for the positive samples
            prepared.positiveSampleIds.forEach((id) => {
                toggleSampleSelection(id);
            });
            // Use the store update function
            setClassifierSamples(prepared);
        } catch (err) {
            error.set(err as Error);
            return Promise.reject(err as Error);
        }
    };

    async function startRefinment(
        mode: RefineMode,
        classifierID: string,
        classifierName: string,
        classifierClasses: string[],
        datasetId: string
    ) {
        try {
            error.set(null);
            await getSamplesToRefine(classifierID, datasetId, classifierClasses);
            openRefineClassifiersPanel('existing', classifierID, classifierName, classifierClasses);
            goto(routeHelpers.toClassifiers(datasetId));
        } catch (err) {
            error.set(err as Error);
        }
    }

    async function refineClassifier(
        classifierID: string,
        datasetId: string,
        classifierClasses: string[]
    ) {
        try {
            error.set(null);
            // Get all sample IDs from prepared samples
            const currentClassifierSamples = get(classifierSamples);
            const allSampleIds = currentClassifierSamples
                ? [
                      ...currentClassifierSamples.positiveSampleIds,
                      ...currentClassifierSamples.negativeSampleIds
                  ]
                : [];
            //Convert selectedSampleIds Set to array using get()
            const currentSelectedIds = get(selectedSampleIds);
            const positiveIds = Array.from(currentSelectedIds);

            // Calculate negative IDs by filtering allSampleIds
            const negativeIds = allSampleIds.filter((id) => !currentSelectedIds.has(id));

            // Create the annotated samples object
            const annotatedSamples = {
                annotations: {
                    positive: positiveIds,
                    negative: negativeIds
                }
            };
            clearSelectedSamples();
            await utils.updateAnnotations(classifierID, annotatedSamples);
            await utils.trainClassifier(classifierID);

            await getSamplesToRefine(classifierID, datasetId, classifierClasses);
        } catch (err) {
            error.set(err as Error);
        }
    }

    async function showClassifierTrainingSamples(
        classifierID: string,
        datasetId: string,
        classifierClasses: string[],
        toggle: boolean
    ) {
        try {
            error.set(null);
            clearSelectedSamples();
            if (toggle) {
                const response = await sampleHistory({
                    path: {
                        classifier_id: classifierID
                    }
                });

                const samples = response.data?.samples;
                if (!samples) {
                    error.set(new Error('No samples data received'));
                    return;
                }

                const keys = Object.keys(samples);

                if (keys.length !== 2) {
                    error.set(new Error('Invalid samples response structure'));
                    return;
                }
                // Check if all classes exist in keys
                if (!classifierClasses.every((className) => keys.includes(className))) {
                    error.set(
                        new Error(`Invalid class names. Expected classes: ${keys.join(', ')}`)
                    );
                    return;
                }
                // Create the prepared samples object
                const prepared = {
                    positiveSampleIds: samples[classifierClasses[0]] || [],
                    negativeSampleIds: samples[classifierClasses[1]] || []
                };

                // Update the selection for the positive samples
                prepared.positiveSampleIds.forEach((id) => {
                    toggleSampleSelection(id);
                });
                // Use the store update function
                setClassifierSamples(prepared);
            } else {
                await getSamplesToRefine(classifierID, datasetId, classifierClasses);
            }
        } catch (err) {
            error.set(err as Error);
        }
    }

    // Wrapper function to handle errors from utility functions
    const prepareSamples = async (): Promise<PrepareSamplesResponse> => {
        try {
            error.set(null);
            const result = await utils.prepareSamples();
            return result;
        } catch (err) {
            error.set(err as Error);
            throw err;
        }
    };

    const saveClassifier = async (
        classifierId: string,
        exportType: ClassifierExportType
    ): Promise<void> => {
        try {
            error.set(null);
            await utils.saveClassifier(classifierId, exportType);
        } catch (err) {
            error.set(err as Error);
            throw err;
        }
    };

    const loadClassifier = async (event: Event): Promise<void> => {
        try {
            error.set(null);
            await utils.loadClassifier(event);
            // Refresh classifiers list after loading (now synchronous)
            loadClassifiers();
        } catch (err) {
            error.set(err as Error);
            throw err;
        }
    };

    const updateAnnotations = async (
        classifierId: string,
        annotations: AnnotatedSamples
    ): Promise<void> => {
        try {
            error.set(null);
            await utils.updateAnnotations(classifierId, annotations);
        } catch (err) {
            error.set(err as Error);
            throw err;
        }
    };

    const trainClassifier = async (classifierId: string): Promise<void> => {
        try {
            error.set(null);
            await utils.trainClassifier(classifierId);
        } catch (err) {
            error.set(err as Error);
            throw err;
        }
    };

    return {
        classifiers: readonly(classifiersData),
        createClassifier,
        loadClassifiers,
        classifiersSelected: readonly(utils.classifiersSelected),
        classifierSelectionToggle: utils.classifierSelectionToggle,
        clearClassifiersSelected: utils.clearClassifiersSelected,
        apply,
        saveClassifier,
        updateAnnotations,
        trainClassifier,
        commitTempClassifier,
        getSamplesToRefine,
        prepareSamples,
        loadClassifier,
        startCreateClassifier,
        isLoading: readonly(isLoading),
        startRefinment,
        showClassifierTrainingSamples,
        refineClassifier,
        error: readonly(error)
    };
}
