import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useClassifiers } from './useClassifiers';
import { get } from 'svelte/store';
import type { ClassifierInfo, Response } from '$lib/services/types';
import collection from '$lib/services/collection';
import { waitFor } from '@testing-library/svelte';
import { useGlobalStorage } from '../useGlobalStorage';
import { useClassifierState } from './useClassifierState';
import * as utils from '$lib/utils';
import client from '$lib/services/collection';

vi.mock('$app/state', () => ({
    page: {
        params: { collection_id: 'test-collection-id' } // Mock collection_id in page params
    }
}));
vi.mock('$app/navigation', () => ({
    goto: vi.fn()
}));

type QueryResult = {
    data: {
        classifiers: ClassifierInfo[];
    } | null;
    isLoading: boolean;
    error: Error | null;
};

const mockClassifiers: ClassifierInfo[] = [
    { classifier_id: '1', classifier_name: 'classifier 1', class_list: ['c1', 'c2'] },
    { classifier_id: '2', classifier_name: 'classifier 2', class_list: ['c3', 'c4'] },
    { classifier_id: '3', classifier_name: 'classifier 3', class_list: ['c5', 'c6'] }
];

describe('useClassifiers Hook', () => {
    const setup = (
        result: QueryResult = {
            data: {
                classifiers: mockClassifiers // API returns { classifiers: [...] }
            },
            isLoading: false,
            error: null
        }
    ) => {
        return vi.spyOn(collection, 'GET').mockResolvedValueOnce(result);
    };

    beforeEach(() => {
        // Reset all mocks before each test
        vi.clearAllMocks();
        vi.resetAllMocks();
        setup();

        const { classifiers } = useGlobalStorage();
        const { clearClassifierSamples } = useClassifierState();
        classifiers.set([]);
        clearClassifierSamples(); // Clear any previous classifier samples
    });
    describe('Classifier Handling', () => {
        it('should initialize with empty selected classifiers', () => {
            const { classifiersSelected } = useClassifiers();
            expect(get(classifiersSelected).size).toBe(0);
        });

        it('should return all classifiers', async () => {
            const { classifiers } = useClassifiers();

            await waitFor(() => expect(get(classifiers)).toEqual(mockClassifiers));
        });

        it('should toggle selection', () => {
            const { classifiersSelected, classifierSelectionToggle } = useClassifiers();

            // Toggle on
            classifierSelectionToggle('1');
            expect(get(classifiersSelected).has('1')).toBe(true);

            // Toggle same off
            classifierSelectionToggle('1');
            expect(get(classifiersSelected).has('1')).toBe(false);
        });

        it('should handle error state', async () => {
            const testError = new Error('Test error');

            // Mock error state
            vi.spyOn(collection, 'GET').mockRejectedValueOnce(testError);

            const { error, classifiers } = useClassifiers();

            expect(get(classifiers)).toEqual([]);

            await waitFor(() => {
                expect(get(error)).toEqual(testError);
            });
        });

        it('should handle multiple selections', () => {
            const { classifiersSelected, clearClassifiersSelected, classifierSelectionToggle } =
                useClassifiers();

            clearClassifiersSelected();
            // Toggle on
            classifierSelectionToggle('1');
            classifierSelectionToggle('2');

            const selected = get(classifiersSelected);
            expect(selected.size).toBe(2);
            expect(selected.has('1')).toBe(true);
            expect(selected.has('2')).toBe(true);
        });

        it('should clear all selected classifiers', () => {
            const { classifiersSelected, clearClassifiersSelected, classifierSelectionToggle } =
                useClassifiers();

            // Toggle some classifiers on
            classifierSelectionToggle('1');
            classifierSelectionToggle('2');

            // Clear all selections
            clearClassifiersSelected();

            expect(get(classifiersSelected).size).toBe(0);
        });

        it('should save classifier successfully', async () => {
            // Mock the POST request
            const mockBlob = new Blob(['test data'], { type: 'application/octet-stream' });
            const mockResponse = {
                data: mockBlob,
                response: {
                    headers: {
                        get: (name: string) => {
                            if (name === 'content-disposition') {
                                return 'attachment; filename="test_classifier.pkl"';
                            }
                            return null;
                        }
                    }
                }
            } as Response;

            const postSpy = vi.spyOn(client, 'POST').mockResolvedValueOnce(mockResponse);
            const downloadSpy = vi.spyOn(utils, 'triggerDownloadBlob').mockImplementation(() => {}); // Update this line
            const { saveClassifier, error } = useClassifiers();
            await saveClassifier('test-id');

            // Verify POST request
            expect(postSpy).toHaveBeenCalledWith(
                '/api/classifiers/{classifier_id}/save_classifier_to_file/{export_type}',
                {
                    params: {
                        path: { classifier_id: 'test-id' }
                    },
                    responseType: 'arraybuffer',
                    headers: {
                        Accept: 'application/octet-stream'
                    },
                    parseAs: 'blob'
                }
            );

            // Verify download triggered
            expect(downloadSpy).toHaveBeenCalledWith('test_classifier.pkl', mockBlob);
            expect(get(error)).toBeNull();
        });

        it('should handle save classifier error', async () => {
            const testError = new Error('Failed to save classifier');
            vi.spyOn(client, 'POST').mockRejectedValueOnce(testError);

            const { saveClassifier, error } = useClassifiers();

            // The main hook should catch the error from the utility and set it in its error store
            await expect(saveClassifier('test-id', 'pkl')).rejects.toThrow(
                'Failed to save classifier'
            );
            expect(get(error)).toEqual(testError);
        });

        it('should load classifier successfully', async () => {
            // Mock file and event
            const mockFile = new File(['test data'], 'test_classifier.pkl', {
                type: 'application/octet-stream'
            });
            const mockEvent = {
                target: {
                    files: [mockFile],
                    value: 'test_classifier.pkl'
                }
            } as unknown as Event;

            // Mock the POST request
            const postSpy = vi.spyOn(client, 'POST').mockResolvedValueOnce({});
            const loadSpy = vi.spyOn(collection, 'GET').mockResolvedValueOnce({
                data: { classifiers: mockClassifiers }
            });

            const { loadClassifier, error } = useClassifiers();
            await loadClassifier(mockEvent, 'test-collection-id');

            // Verify POST request
            expect(postSpy).toHaveBeenCalledWith('/api/classifiers/load_classifier_from_buffer', {
                params: {
                    query: { collection_id: 'test-collection-id' }
                },
                body: expect.any(FormData),
                headers: {
                    Accept: 'application/json'
                }
            });

            // Verify classifiers were reloaded with collection_id
            expect(loadSpy).toHaveBeenCalledWith('/api/classifiers/get_all_classifiers', {
                params: {
                    query: { collection_id: 'test-collection-id' }
                }
            });

            // Verify input was reset
            expect((mockEvent.target as HTMLInputElement).value).toBe('');
            expect(get(error)).toBeNull();
        });

        it('should handle load classifier error', async () => {
            // Mock file and event
            const mockFile = new File(['test data'], 'test_classifier.pkl', {
                type: 'application/octet-stream'
            });
            const mockEvent = {
                target: {
                    files: [mockFile],
                    value: 'test_classifier.pkl'
                }
            } as unknown as Event;

            const testError = new Error('Failed to load classifier');
            vi.spyOn(client, 'POST').mockRejectedValueOnce(testError);
            const { loadClassifier, error } = useClassifiers();

            // The function should throw the error, but we can catch it and check the error store
            try {
                await loadClassifier(mockEvent, 'test-collection-id');
            } catch {
                // Error is expected to be thrown
            }

            expect(get(error)).toEqual(testError);
        });
    });
    describe('Classifier Creation and Preparation', () => {
        it('should prepare samples successfully', async () => {
            const mockPositives = ['1', '2'];
            const mockResponse = {
                data: {
                    negative_sample_ids: ['3', '4']
                }
            };

            const { selectedSampleIdsByCollection } = useGlobalStorage();
            selectedSampleIdsByCollection.update((state) => ({
                ...state,
                'test-collection-id': new Set(mockPositives)
            }));

            const postSpy = vi.spyOn(client, 'POST').mockResolvedValueOnce(mockResponse);

            const { prepareSamples } = useClassifiers();
            const result = await prepareSamples();

            expect(postSpy).toHaveBeenCalledWith('/api/classifiers/get_negative_samples', {
                body: {
                    collection_id: 'test-collection-id',
                    positive_sample_ids: mockPositives
                }
            });

            expect(result).toEqual({
                positiveSampleIds: mockPositives,
                negativeSampleIds: ['3', '4']
            });
        });

        it('should create classifier successfully', async () => {
            const mockRequest = {
                name: 'Test Classifier',
                class_list: ['positive', 'negative'],
                collection_id: 'test-collection-id'
            };

            // Mock the initial classifier creation response
            const mockCreateResponse = {
                data: {
                    name: 'Test Classifier',
                    classifier_id: '12134'
                },
                error: null
            };

            // Mock the classifier samples
            const mockClassifierSamples = {
                positiveSampleIds: ['1', '2'],
                negativeSampleIds: ['3', '4']
            };

            // Set up the initial state
            const { classifierSamples, classifierSelectedSampleIds } = useClassifierState();
            classifierSamples.set(mockClassifierSamples);
            classifierSelectedSampleIds.set(new Set(['1', '2']));

            // Set up all the required spies
            const postSpy = vi.spyOn(client, 'POST');
            postSpy
                .mockResolvedValueOnce(mockCreateResponse) // createClassifier
                .mockResolvedValueOnce({}) // updateAnnotations
                .mockResolvedValueOnce({}); // trainClassifier
            const mockSamplesResponse = {
                data: {
                    samples: {
                        positive: ['1', '2'],
                        negative: ['3', '4']
                    }
                },
                error: null,
                response: new globalThis.Response()
            };
            const getSpy = vi.spyOn(client, 'GET').mockResolvedValueOnce(mockSamplesResponse); // getSamplesToRefine

            const { createClassifier } = useClassifiers();
            const result = await createClassifier(mockRequest);
            // Verify the initial classifier creation
            expect(postSpy).toHaveBeenCalledWith('/api/classifiers/create', {
                body: {
                    name: mockRequest.name,
                    class_list: mockRequest.class_list,
                    collection_id: mockRequest.collection_id
                }
            });

            //Verify annotations were updated
            expect(postSpy).toHaveBeenCalledWith(
                '/api/classifiers/{classifier_id}/update_annotations',
                {
                    params: {
                        path: { classifier_id: '12134' }
                    },
                    body: {
                        annotations: {
                            positive: ['1', '2'],
                            negative: ['3', '4']
                        }
                    }
                }
            );

            // Verify training was triggered
            expect(postSpy).toHaveBeenCalledWith(
                '/api/classifiers/{classifier_id}/train_classifier',
                {
                    params: {
                        path: { classifier_id: '12134' }
                    }
                }
            );

            // Verify samples were fetched for refinement
            expect(getSpy).toHaveBeenCalledWith(
                '/api/classifiers/{classifier_id}/samples_to_refine',
                {
                    params: {
                        path: { classifier_id: '12134' },
                        query: { collection_id: 'test-collection-id' }
                    }
                }
            );

            // Verify the final result
            expect(result).toEqual(mockCreateResponse.data);
        }, 10000);
    });
    describe('Classifier Refinement', () => {
        it('should get samples to refine successfully', async () => {
            // Mock the full API response structure exactly
            const mockGetResponse = {
                data: {
                    samples: {
                        positive: ['1', '2'],
                        negative: ['3', '4']
                    }
                },
                response: new globalThis.Response(),
                error: null
            };

            // Mock the GET request with exact response structure
            const getSpy = vi
                .spyOn(client, 'GET')
                .mockImplementation(() => Promise.resolve(mockGetResponse));

            // Execute test
            const { getSamplesToRefine } = useClassifiers();
            await getSamplesToRefine('classifier-id', 'collection-id', ['positive', 'negative']);

            // Verify API call
            expect(getSpy).toHaveBeenCalledWith(
                '/api/classifiers/{classifier_id}/samples_to_refine',
                {
                    params: {
                        path: { classifier_id: 'classifier-id' },
                        query: { collection_id: 'collection-id' }
                    }
                }
            );

            // Verify store updates
            const { classifierSamples } = useClassifierState();
            expect(get(classifierSamples)).toEqual({
                positiveSampleIds: ['1', '2'],
                negativeSampleIds: ['3', '4']
            });
        });

        it('should get all training samples successfully', async () => {
            // Mock the sampleHistory function from lightly_studio_local
            const mockSampleHistoryResponse = {
                data: {
                    samples: {
                        positive: ['1', '2'],
                        negative: ['3', '4']
                    }
                },
                response: new globalThis.Response(),
                error: null
            };

            // Mock the sampleHistory function
            const sampleHistoryModule = await import('$lib/api/lightly_studio_local');
            const sampleHistorySpy = vi
                .spyOn(sampleHistoryModule, 'sampleHistory')
                .mockResolvedValue(mockSampleHistoryResponse);

            // Execute test
            const { showClassifierTrainingSamples } = useClassifiers();
            await showClassifierTrainingSamples(
                'classifier-id',
                'collection-id',
                ['positive', 'negative'],
                true
            );

            // Verify API call
            expect(sampleHistorySpy).toHaveBeenCalledWith({
                path: { classifier_id: 'classifier-id' }
            });

            // Verify store updates
            const { classifierSamples } = useClassifierState();
            expect(get(classifierSamples)).toEqual({
                positiveSampleIds: ['1', '2'],
                negativeSampleIds: ['3', '4']
            });
        });

        it('should refine classifier successfully', async () => {
            const mockClassifierSamples = {
                positiveSampleIds: ['1', '2'],
                negativeSampleIds: ['3', '4']
            };

            const { classifierSamples } = useClassifierState();
            const { selectedSampleIdsByCollection } = useGlobalStorage();
            classifierSamples.set(mockClassifierSamples);
            selectedSampleIdsByCollection.update((state) => ({
                ...state,
                'collection-id': new Set(['1', '2'])
            }));

            const updateSpy = vi.spyOn(client, 'POST').mockResolvedValue({});

            const { refineClassifier } = useClassifiers();
            await refineClassifier('classifier-id', 'collection-id', ['positive', 'negative']);

            expect(updateSpy).toHaveBeenCalledTimes(2); // updateAnnotations and trainClassifier
        });
    });

    describe('Classifier Training and Committing', () => {
        it('should train classifier successfully', async () => {
            const trainSpy = vi.spyOn(client, 'POST').mockResolvedValue({});

            const { trainClassifier } = useClassifiers();
            await trainClassifier('classifier-id');

            expect(trainSpy).toHaveBeenCalledWith(
                '/api/classifiers/{classifier_id}/train_classifier',
                expect.any(Object)
            );
        });

        it('should commit temporary classifier successfully', async () => {
            // Mock the global storage first
            const { selectedSampleIdsByCollection } = useGlobalStorage();

            // Set some initial state to clear
            selectedSampleIdsByCollection.update((state) => ({
                ...state,
                'collection-id': new Set(['1', '2'])
            }));

            // Mock API responses
            const commitSpy = vi.spyOn(client, 'POST').mockResolvedValue({});
            const loadSpy = vi.spyOn(client, 'GET').mockResolvedValue({
                data: { classifiers: mockClassifiers }
            });

            // Execute test
            const { commitTempClassifier } = useClassifiers();
            await commitTempClassifier('test-classifier-id', 'test-collection-id');

            // Verify API calls
            expect(commitSpy).toHaveBeenCalledWith(
                '/api/classifiers/{classifier_id}/commit_temp_classifier',
                {
                    params: {
                        path: { classifier_id: 'test-classifier-id' }
                    }
                }
            );

            // Verify classifiers were reloaded with collection_id
            expect(loadSpy).toHaveBeenCalledWith('/api/classifiers/get_all_classifiers', {
                params: {
                    query: { collection_id: 'test-collection-id' }
                }
            });
        });
    });

    describe('Classifier Annotations', () => {
        it('should update annotations successfully', async () => {
            const mockAnnotations = {
                annotations: {
                    positive: ['1', '2'],
                    negative: ['3', '4']
                }
            };

            const updateSpy = vi.spyOn(client, 'POST').mockResolvedValue({});

            const { updateAnnotations } = useClassifiers();
            await updateAnnotations('classifier-id', mockAnnotations);

            expect(updateSpy).toHaveBeenCalledWith(
                '/api/classifiers/{classifier_id}/update_annotations',
                expect.any(Object)
            );
        });
    });

    describe('Error Handling', () => {
        it('should handle prepare samples error', async () => {
            const testError = new Error('Failed to prepare samples');
            vi.spyOn(client, 'POST').mockRejectedValueOnce(testError);

            const { prepareSamples, error } = useClassifiers();

            // The main hook should catch the error from the utility and set it in its error store
            await expect(prepareSamples()).rejects.toThrow('Failed to prepare samples');
            expect(get(error)).toEqual(testError);
        });

        it("should handle getSamplesToRefine error when classes don't match", async () => {
            // Mock response with different classes than what we'll request
            const mockGetResponse = {
                data: {
                    samples: {
                        class1: ['1', '2'],
                        class2: ['3', '4']
                    }
                },
                response: new globalThis.Response(),
                error: null
            };

            // Set up spy
            const getSpy = vi
                .spyOn(client, 'GET')
                .mockImplementation(() => Promise.resolve(mockGetResponse));
            // Execute test with mismatched classes
            const { getSamplesToRefine, error } = useClassifiers();
            await getSamplesToRefine('classifier-id', 'collection-id', ['positive', 'negative']);

            // Verify API was called
            expect(getSpy).toHaveBeenCalledWith(
                '/api/classifiers/{classifier_id}/samples_to_refine',
                {
                    params: {
                        path: { classifier_id: 'classifier-id' },
                        query: { collection_id: 'collection-id' }
                    }
                }
            );

            // Verify error was set with correct message
            expect(get(error)?.message).toBe(
                'Invalid class names. Expected classes: class1, class2'
            );

            // Verify store wasn't updated
            const { classifierSamples } = useClassifierState();
            expect(get(classifierSamples)).toBeNull();
        });
    });
});
