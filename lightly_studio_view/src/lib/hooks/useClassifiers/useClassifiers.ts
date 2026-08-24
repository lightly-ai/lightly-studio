import type {
    ClassifierInfo,
    AnnotatedSamples,
    RefineMode,
    ClassifierExportType
} from '$lib/services/types';
import { page } from '$app/state';
import { get, readonly, type Readable, writable } from 'svelte/store';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';
import { useClassifierState } from './useClassifierState';
import { useClassifierWorkflow } from '$lib/hooks/useClassifiers/useClassifierWorkflow';
import { CLASSIFIER_CREATION_CANDIDATE_LIMIT } from './classifierCandidates';
import { toast } from 'svelte-sonner';
import {
    getAllClassifiers,
    createClassifier as createClassifierApi,
    runClassifierRoute,
    samplesToRefine,
    commitTempClassifier as commitTempClassifierApi,
    dropTempClassifier as dropTempClassifierApi,
    sampleHistory
} from '$lib/api/lightly_studio_local';
import type {
    CreateClassifierRequest,
    CreateClassifierResponse
} from '$lib/api/lightly_studio_local';

// Import the utility functions
import { useClassifierUtils } from './useClassifierUtils';

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
    commitTempClassifier: (classifierId: string, collectionId: string) => Promise<void>;
    dropTempClassifier: (classifierId: string) => Promise<void>;
    getSamplesToRefine: (
        classifierId: string,
        collectionId: string,
        classifierClasses: string[]
    ) => Promise<void>;
    prepareSamples: (positiveSampleIds: string[]) => Promise<PrepareSamplesResponse>;
    loadClassifier: (event: Event, collectionId: string) => Promise<void>;
    startCreateClassifier: () => void;
    startRefinement: (
        mode: RefineMode,
        classifierId: string,
        classifierName: string,
        classifierClasses: string[],
        collectionId: string
    ) => Promise<void>;
    applyClassifierCorrections: (classifierId: string) => Promise<void>;
    refineClassifier: (
        classifierID: string,
        collectionId: string,
        classifierClasses: string[]
    ) => Promise<void>;
    showClassifierTrainingSamples: (
        classifierID: string,
        collectionId: string,
        classifierClasses: string[],
        toggle: boolean
    ) => Promise<void>;
}

export function useClassifiers(): UseClassifiersReturn {
    const { classifiers: classifiersData, getSelectedSampleIds } = useGlobalStorage();
    const {
        classifierSamples,
        setClassifierSamples,
        clearClassifierSamples,
        classifierSelectedSampleIds,
        clearClassifierSelectedSamples,
        toggleClassifierSampleSelection
    } = useClassifierState();

    // Use the utility functions
    const utils = useClassifierUtils();
    const error = writable<Error | null>(null);
    const isLoading = writable(false);
    const isLoaded = writable(false);
    const { openCreate, openRefine, setTemporaryClassifier } = useClassifierWorkflow();

    const loadClassifiers = async () => {
        if (get(isLoading)) return;
        error.set(null);
        isLoading.set(true);

        try {
            const response = await getAllClassifiers({
                query: { collection_id: page.params.collection_id! }
            });
            if (response.data?.classifiers) {
                // Extract just the classifiers array from the response.
                classifiersData.set(response.data.classifiers);
            } else {
                classifiersData.set([]); // Set empty array if no data.
            }
        } catch (err) {
            error.set(err as Error);
        } finally {
            isLoading.set(false);
        }
    };

    // Initialize classifiers on hook creation
    if (!get(isLoaded)) {
        loadClassifiers();
        isLoaded.set(true);
    }

    function startCreateClassifier() {
        error.set(null);
        clearClassifierSamples();
        clearClassifierSelectedSamples();
        Array.from(get(getSelectedSampleIds(page.params.collection_id!)))
            .slice(0, CLASSIFIER_CREATION_CANDIDATE_LIMIT)
            .forEach((sampleId) => {
                toggleClassifierSampleSelection(sampleId);
            });
        openCreate();
    }

    async function createClassifier(
        request: CreateClassifierRequest
    ): Promise<CreateClassifierResponse> {
        try {
            error.set(null);
            if (!request.collection_id) {
                throw new Error('Collection ID is required');
            }

            const positiveIds = Array.from(get(classifierSelectedSampleIds));
            if (positiveIds.length === 0) {
                throw new Error('Select at least one matching example.');
            }
            const preparedSamples = await utils.prepareSamples(positiveIds);

            const response = await createClassifierApi({
                body: {
                    name: request.name,
                    class_list: request.class_list,
                    collection_id: request.collection_id.toString()
                }
            });

            if (!response.data) {
                error.set(Error('Failed to create classifier.'));
                return Promise.reject('Failed to create classifier.');
            }

            setTemporaryClassifier(
                response.data.classifier_id,
                response.data.name,
                request.class_list
            );

            const annotatedSamples = {
                annotations: {
                    positive: positiveIds,
                    negative: preparedSamples.negativeSampleIds
                }
            };
            await utils.updateAnnotations(response.data.classifier_id, annotatedSamples);
            await utils.trainClassifier(response.data.classifier_id);

            await getSamplesToRefine(
                response.data.classifier_id,
                request.collection_id.toString(),
                request.class_list
            );
            openRefine('temp', response.data.classifier_id, response.data.name, request.class_list);
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

                    await runClassifierRoute({
                        path: {
                            classifier_id: classifier_id,
                            collection_id: page.params.collection_id!
                        }
                    });

                    // Show toast for each classifier run
                    toast.success(
                        `Classifier "${classifier.classifier_name}" completed successfully. ` +
                            `New annotation classes added: ${generatedLabels.join(', ')}. ` +
                            `Annotations have been added to your collection.`,
                        {
                            duration: 10000
                        }
                    );
                }
            }

            isLoading.set(false);
        } catch (err) {
            isLoading.set(false);
            error.set(err as Error);
            toast.error('Failed to run classifiers: ' + (err as Error).message);
        }
    };

    const commitTempClassifier = async (classifierId: string) => {
        try {
            error.set(null);
            await commitTempClassifierApi({
                path: { classifier_id: classifierId }
            });
            await loadClassifiers();
        } catch (err) {
            error.set(err as Error);
            throw err;
        }

        clearClassifierSamples();
    };

    const dropTempClassifier = async (classifierId: string): Promise<void> => {
        try {
            error.set(null);
            await dropTempClassifierApi({ path: { classifier_id: classifierId } });
        } catch (err) {
            error.set(err as Error);
            throw err;
        }
    };

    const getSamplesToRefine = async (
        classifierId: string,
        collectionId: string,
        classes: string[]
    ) => {
        try {
            error.set(null);
            const response = await samplesToRefine({
                path: { classifier_id: classifierId },
                query: { collection_id: collectionId }
            });

            // Handle case where no samples are returned
            if (!response.data?.samples) {
                // Clear the store to show empty state
                setClassifierSamples({
                    positiveSampleIds: [],
                    negativeSampleIds: []
                });
                clearClassifierSelectedSamples();
                return;
            }

            const samples = response.data.samples;
            const keys = Object.keys(samples);

            if (keys.length !== 2) {
                throw new Error('Invalid samples response structure');
            }
            // Check if all classes exist in keys
            if (!classes.every((className) => keys.includes(className))) {
                throw new Error(`Invalid class names. Expected classes: ${keys.join(', ')}`);
            }
            // Create the prepared samples object
            const prepared = {
                positiveSampleIds: samples[classes[0]] || [],
                negativeSampleIds: samples[classes[1]] || []
            };

            // Clear any existing selections and set the positive samples as selected
            clearClassifierSelectedSamples();
            prepared.positiveSampleIds.forEach((id) => {
                toggleClassifierSampleSelection(id);
            });

            // Use the store update function
            setClassifierSamples(prepared);
        } catch (err) {
            error.set(err as Error);
            return Promise.reject(err as Error);
        }
    };

    async function startRefinement(
        mode: RefineMode,
        classifierID: string,
        classifierName: string,
        classifierClasses: string[],
        collectionId: string
    ) {
        clearClassifierSamples();
        clearClassifierSelectedSamples();
        openRefine(mode, classifierID, classifierName, classifierClasses);
        try {
            error.set(null);
            await getSamplesToRefine(classifierID, collectionId, classifierClasses);
        } catch (err) {
            error.set(err as Error);
        }
    }

    async function refineClassifier(
        classifierID: string,
        collectionId: string,
        classifierClasses: string[]
    ) {
        try {
            await applyClassifierCorrections(classifierID);
            await getSamplesToRefine(classifierID, collectionId, classifierClasses);
        } catch (err) {
            error.set(err as Error);
            throw err;
        }
    }

    async function applyClassifierCorrections(classifierId: string): Promise<void> {
        try {
            error.set(null);
            const samples = get(classifierSamples);
            const positiveIds = Array.from(get(classifierSelectedSampleIds));
            const positiveIdSet = new Set(positiveIds);
            const reviewedIds = samples
                ? [...samples.positiveSampleIds, ...samples.negativeSampleIds]
                : [];
            await utils.updateAnnotations(classifierId, {
                annotations: {
                    positive: positiveIds,
                    negative: reviewedIds.filter((sampleId) => !positiveIdSet.has(sampleId))
                }
            });
            await utils.trainClassifier(classifierId);
        } catch (err) {
            error.set(err as Error);
            throw err;
        }
    }

    async function showClassifierTrainingSamples(
        classifierID: string,
        collectionId: string,
        classifierClasses: string[],
        toggle: boolean
    ) {
        try {
            error.set(null);
            if (toggle) {
                const response = await sampleHistory({
                    path: {
                        classifier_id: classifierID
                    }
                });

                const samples = response.data?.samples;
                if (!samples) {
                    throw new Error('No samples data received');
                }

                const keys = Object.keys(samples);

                if (keys.length !== 2) {
                    throw new Error('Invalid samples response structure');
                }
                // Check if all classes exist in keys
                if (!classifierClasses.every((className) => keys.includes(className))) {
                    throw new Error(`Invalid class names. Expected classes: ${keys.join(', ')}`);
                }
                // Create the prepared samples object
                const prepared = {
                    positiveSampleIds: samples[classifierClasses[0]] || [],
                    negativeSampleIds: samples[classifierClasses[1]] || []
                };

                // Clear any existing selections and set the positive samples as selected
                clearClassifierSelectedSamples();
                prepared.positiveSampleIds.forEach((id) => {
                    toggleClassifierSampleSelection(id);
                });

                // Use the store update function
                setClassifierSamples(prepared);
            } else {
                await getSamplesToRefine(classifierID, collectionId, classifierClasses);
            }
        } catch (err) {
            error.set(err as Error);
            throw err;
        }
    }

    // Wrapper function to handle errors from utility functions
    const prepareSamples = async (positiveSampleIds: string[]): Promise<PrepareSamplesResponse> => {
        try {
            error.set(null);
            const result = await utils.prepareSamples(positiveSampleIds);
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

    const loadClassifier = async (event: Event, collectionId: string): Promise<void> => {
        try {
            error.set(null);
            await utils.loadClassifier(event, collectionId);
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
        dropTempClassifier,
        getSamplesToRefine,
        prepareSamples,
        loadClassifier,
        startCreateClassifier,
        isLoading: readonly(isLoading),
        startRefinement,
        applyClassifierCorrections,
        showClassifierTrainingSamples,
        refineClassifier,
        error: readonly(error)
    };
}
