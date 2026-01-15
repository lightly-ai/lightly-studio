import { readCollection, readDataset } from '$lib/api/lightly_studio_local/sdk.gen';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { LayoutLoadEvent } from './$types';
import { load } from './+layout';
import { routeHelpers } from '$lib/routes';
import { SampleType } from '$lib/api/lightly_studio_local';

// Mock the service imports
vi.mock('$lib/api/lightly_studio_local/sdk.gen');
vi.mock('@sveltejs/kit', () => ({
    redirect: vi.fn((status, location) => {
        const error = new Error('Redirect');
        (error as any).status = status;
        (error as any).location = location;
        throw error;
    })
}));

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

        vi.mocked(readDataset).mockResolvedValue({
            data: mockRootCollection,
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

        expect(result.datasetId).toBe(mockDatasetId);
        expect(result.collectionType).toBe(mockCollectionType);
        expect(result.collectionId).toBe(mockCollectionId);
        expect(result.collection).toBeDefined();
        expect(result.globalStorage).toBeDefined();
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
        } catch (error: any) {
            expect(error.status).toBe(307);
            expect(error.location).toBe(routeHelpers.toHome());
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
        } catch (error: any) {
            expect(error.status).toBe(307);
            expect(error.location).toBe(routeHelpers.toHome());
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
        } catch (error: any) {
            expect(error.status).toBe(307);
            expect(error.location).toBe(routeHelpers.toHome());
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
        } catch (error: any) {
            expect(error.status).toBe(307);
            expect(error.location).toBe(
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
        } catch (error: any) {
            expect(error.status).toBe(307);
            expect(error.location).toBe(routeHelpers.toHome());
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
        } catch (error: any) {
            expect(error.status).toBe(307);
            expect(error.location).toBe(routeHelpers.toHome());
        }
    });

    it('should redirect when dataset_id does not match root collection', async () => {
        const differentRootId = '00000000-0000-0000-0000-000000000000';

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

        vi.mocked(readDataset).mockResolvedValue({
            data: {
                ...mockRootCollection,
                collection_id: differentRootId
            },
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
        } catch (error: any) {
            expect(error.status).toBe(307);
            expect(error.location).toBe(
                routeHelpers.toCollectionHome(differentRootId, mockCollectionType, mockCollectionId)
            );
        }
    });

    it('should redirect when rootCollection is null', async () => {
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

        vi.mocked(readDataset).mockResolvedValue({
            data: null,
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
        } catch (error: any) {
            expect(error.status).toBe(307);
            expect(error.location).toBe(routeHelpers.toHome());
        }
    });
});
