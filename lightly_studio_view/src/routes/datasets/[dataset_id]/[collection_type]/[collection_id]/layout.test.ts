import { readCollection, readCollectionHierarchy } from '$lib/api/lightly_studio_local/sdk.gen';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { LayoutLoadEvent } from './$types';
import { load } from './+layout';
import { routeHelpers } from '$lib/routes';
import { SampleType } from '$lib/api/lightly_studio_local';

// Mock the service imports
vi.mock('$lib/api/lightly_studio_local/sdk.gen');
vi.mock('@sveltejs/kit', () => ({
    redirect: vi.fn((status, location) => {
        const error = new Error('Redirect') as Error & { status: number; location: string };
        error.status = status;
        error.location = location;
        throw error;
    }),
    error: vi.fn((status, message) => {
        const err = new Error(message) as Error & { status: number };
        err.status = status;
        throw err;
    })
}));

type RedirectError = Error & { status: number; location: string };

describe('+layout.ts', () => {
    const mockDatasetId = '123e4567-e89b-12d3-a456-426614174000';
    const mockCollectionId = '987fcdeb-51a2-43d7-8f9e-123456789abc';
    const mockCollectionType = 'image';

    const mockCollection = {
        collection_id: mockCollectionId,
        name: 'Test Collection',
        sample_type: SampleType.IMAGE,
        parent_collection_id: mockDatasetId
    };

    const mockDataset = {
        collection_id: mockDatasetId,
        name: 'Test Dataset',
        sample_type: SampleType.IMAGE,
        parent_collection_id: null
    };

    const mockRootCollection = {
        collection_id: mockDatasetId,
        name: 'Test Dataset',
        sample_type: SampleType.IMAGE
    };

    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should load collection and return data with valid params', async () => {
        vi.mocked(readCollection)
            .mockResolvedValueOnce({
                data: mockCollection,
                request: undefined,
                response: undefined
            })
            .mockResolvedValueOnce({
                data: mockDataset,
                request: undefined,
                response: undefined
            });

        // Mock readCollectionHierarchy to return a flat list including both dataset and collection
        vi.mocked(readCollectionHierarchy).mockResolvedValue({
            data: [mockDataset, mockCollection],
            request: undefined,
            response: undefined
        });

        const result = await load({
            params: {
                dataset_id: mockDatasetId,
                collection_type: mockCollectionType,
                collection_id: mockCollectionId
            }
        } as LayoutLoadEvent);

        expect(result.collection).toBeDefined();
        expect(result.collection?.collection_id).toBe(mockCollectionId);
        expect(result.globalStorage).toBeDefined();
        expect(result.selectedAnnotationFilterIds).toBeDefined();
        expect(result.sampleSize).toBeDefined();
    });

    it('should load collection when collection_id equals dataset_id (root collection)', async () => {
        // When collection_id === dataset_id, we don't need to check hierarchy
        vi.mocked(readCollection)
            .mockResolvedValueOnce({
                data: mockDataset, // Collection is the dataset itself
                request: undefined,
                response: undefined
            })
            .mockResolvedValueOnce({
                data: mockDataset, // Dataset collection
                request: undefined,
                response: undefined
            });

        const result = await load({
            params: {
                dataset_id: mockDatasetId,
                collection_type: mockCollectionType,
                collection_id: mockDatasetId // Same as dataset_id
            }
        } as LayoutLoadEvent);

        expect(result.collection).toBeDefined();
        expect(result.collection?.collection_id).toBe(mockDatasetId);
        expect(result.globalStorage).toBeDefined();
        // readCollectionHierarchy should not be called when collection_id === dataset_id
        expect(readCollectionHierarchy).not.toHaveBeenCalled();
    });

    it('should redirect when dataset_id is invalid UUID', async () => {
        try {
            await load({
                params: {
                    dataset_id: 'invalid-uuid',
                    collection_type: mockCollectionType,
                    collection_id: mockCollectionId
                }
            } as LayoutLoadEvent);
            expect.fail('Should have thrown redirect');
        } catch (error: unknown) {
            const redirectError = error as RedirectError;
            expect(redirectError.status).toBe(307);
            expect(redirectError.location).toBe(routeHelpers.toHome());
        }
    });

    it('should redirect when collection_id is invalid UUID', async () => {
        try {
            await load({
                params: {
                    dataset_id: mockDatasetId,
                    collection_type: mockCollectionType,
                    collection_id: 'invalid-uuid'
                }
            } as LayoutLoadEvent);
            expect.fail('Should have thrown redirect');
        } catch (error: unknown) {
            const redirectError = error as RedirectError;
            expect(redirectError.status).toBe(307);
            expect(redirectError.location).toBe(routeHelpers.toHome());
        }
    });

    it('should redirect when collection not found', async () => {
        vi.mocked(readCollection).mockRejectedValue(new Error('Not found'));

        try {
            await load({
                params: {
                    dataset_id: mockDatasetId,
                    collection_type: mockCollectionType,
                    collection_id: mockCollectionId
                }
            } as LayoutLoadEvent);
            expect.fail('Should have thrown redirect');
        } catch (error: unknown) {
            const redirectError = error as RedirectError;
            expect(redirectError.status).toBe(307);
            expect(redirectError.location).toBe(routeHelpers.toHome());
        }
    });

    it('should redirect when collection_type does not match sample_type', async () => {
        const videoCollection = {
            ...mockCollection,
            sample_type: SampleType.VIDEO
        };

        vi.mocked(readCollection).mockResolvedValueOnce({
            data: videoCollection,
            request: undefined,
            response: undefined
        });

        try {
            await load({
                params: {
                    dataset_id: mockDatasetId,
                    collection_type: 'image', // Wrong type
                    collection_id: mockCollectionId
                }
            } as LayoutLoadEvent);
            expect.fail('Should have thrown redirect');
        } catch (error: unknown) {
            const redirectError = error as RedirectError;
            expect(redirectError.status).toBe(307);
            expect(redirectError.location).toBe(
                routeHelpers.toCollectionHome(mockDatasetId, 'video', mockCollectionId)
            );
        }
    });

    it('should redirect when dataset_id does not exist', async () => {
        vi.mocked(readCollection)
            .mockResolvedValueOnce({
                data: mockCollection,
                request: undefined,
                response: undefined
            })
            .mockRejectedValueOnce(new Error('Dataset not found'));

        try {
            await load({
                params: {
                    dataset_id: mockDatasetId,
                    collection_type: mockCollectionType,
                    collection_id: mockCollectionId
                }
            } as LayoutLoadEvent);
            expect.fail('Should have thrown redirect');
        } catch (error: unknown) {
            const redirectError = error as RedirectError;
            expect(redirectError.status).toBe(307);
            expect(redirectError.location).toBe(routeHelpers.toHome());
        }
    });

    it('should redirect when dataset_id is not a root collection', async () => {
        const nonRootDataset = {
            ...mockDataset,
            parent_collection_id: 'some-parent-id'
        };

        vi.mocked(readCollection)
            .mockResolvedValueOnce({
                data: mockCollection,
                request: undefined,
                response: undefined
            })
            .mockResolvedValueOnce({
                data: nonRootDataset,
                request: undefined,
                response: undefined
            });

        try {
            await load({
                params: {
                    dataset_id: mockDatasetId,
                    collection_type: mockCollectionType,
                    collection_id: mockCollectionId
                }
            } as LayoutLoadEvent);
            expect.fail('Should have thrown redirect');
        } catch (error: unknown) {
            const redirectError = error as RedirectError;
            expect(redirectError.status).toBe(307);
            expect(redirectError.location).toBe(routeHelpers.toHome());
        }
    });

    it('should throw error when collection does not belong to dataset', async () => {
        const differentCollectionId = '00000000-0000-0000-0000-000000000000';

        vi.mocked(readCollection)
            .mockResolvedValueOnce({
                data: mockCollection,
                request: undefined,
                response: undefined
            })
            .mockResolvedValueOnce({
                data: mockDataset,
                request: undefined,
                response: undefined
            });

        // Mock readCollectionHierarchy to return only the dataset, not the collection
        vi.mocked(readCollectionHierarchy).mockResolvedValue({
            data: [mockDataset], // Collection not in hierarchy
            request: undefined,
            response: undefined
        });

        try {
            await load({
                params: {
                    dataset_id: mockDatasetId,
                    collection_type: mockCollectionType,
                    collection_id: mockCollectionId
                }
            } as LayoutLoadEvent);
            expect.fail('Should have thrown error');
        } catch (err: unknown) {
            const errorObj = err as Error & { status: number };
            expect(errorObj.status).toBe(500);
            expect(errorObj.message).toContain('does not belong to dataset');
        }
    });

    it('should throw error when dataset collection is null', async () => {
        vi.mocked(readCollection)
            .mockResolvedValueOnce({
                data: mockCollection,
                request: undefined,
                response: undefined
            })
            .mockResolvedValueOnce({
                data: null, // Dataset collection is null
                request: undefined,
                response: undefined
            });

        try {
            await load({
                params: {
                    dataset_id: mockDatasetId,
                    collection_type: mockCollectionType,
                    collection_id: mockCollectionId
                }
            } as LayoutLoadEvent);
            expect.fail('Should have thrown error');
        } catch (err: unknown) {
            const errorObj = err as Error & { status: number };
            expect(errorObj.status).toBe(500);
            expect(errorObj.message).toContain('Dataset collection not found');
        }
    });

    it('should throw error when hierarchy fetch fails', async () => {
        vi.mocked(readCollection)
            .mockResolvedValueOnce({
                data: mockCollection,
                request: undefined,
                response: undefined
            })
            .mockResolvedValueOnce({
                data: mockDataset,
                request: undefined,
                response: undefined
            });

        // Mock readCollectionHierarchy to throw an error
        vi.mocked(readCollectionHierarchy).mockRejectedValue(new Error('Hierarchy fetch failed'));

        try {
            await load({
                params: {
                    dataset_id: mockDatasetId,
                    collection_type: mockCollectionType,
                    collection_id: mockCollectionId
                }
            } as LayoutLoadEvent);
            expect.fail('Should have thrown error');
        } catch (err: unknown) {
            const errorObj = err as Error & { status: number };
            expect(errorObj.status).toBe(500);
            expect(errorObj.message).toContain('Error loading collection hierarchy');
        }
    });
});
