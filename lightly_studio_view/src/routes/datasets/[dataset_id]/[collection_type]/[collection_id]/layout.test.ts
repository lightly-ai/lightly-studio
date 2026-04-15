import { readCollection, readCollectionHierarchy } from '$lib/api/lightly_studio_local/sdk.gen';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { LayoutLoadEvent } from './$types';
import { load } from './+layout';
import { routeHelpers } from '$lib/routes';
import { SampleType } from '$lib/api/lightly_studio_local';

const { gotoMock } = vi.hoisted(() => ({
    gotoMock: vi.fn()
}));

// Mock the service imports
vi.mock('$lib/api/lightly_studio_local/sdk.gen');
vi.mock('$app/navigation', () => ({
    goto: gotoMock
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

    beforeEach(() => {
        vi.clearAllMocks();
        gotoMock.mockClear();
        // Reset all mocks to ensure no state leaks between tests
        vi.mocked(readCollection).mockReset();
        vi.mocked(readCollectionHierarchy).mockReset();
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
        expect(result.sampleSize).toBeDefined();
    });

    it('should redirect when dataset_id is invalid UUID', async () => {
        load({
            params: {
                dataset_id: 'invalid-uuid',
                collection_type: mockCollectionType,
                collection_id: mockCollectionId
            }
        } as LayoutLoadEvent);

        // Give it a moment to call goto
        await new Promise((resolve) => setTimeout(resolve, 0));

        expect(gotoMock).toHaveBeenCalledWith(routeHelpers.toHome());
    });

    it('should redirect when collection_id is invalid UUID', async () => {
        load({
            params: {
                dataset_id: mockDatasetId,
                collection_type: mockCollectionType,
                collection_id: 'invalid-uuid'
            }
        } as LayoutLoadEvent);

        // Give it a moment to call goto
        await new Promise((resolve) => setTimeout(resolve, 0));

        expect(gotoMock).toHaveBeenCalledWith(routeHelpers.toHome());
    });

    it('should throw error when collection not found', async () => {
        vi.mocked(readCollection).mockRejectedValueOnce(new Error('Not found'));

        await expect(
            load({
                params: {
                    dataset_id: mockDatasetId,
                    collection_type: mockCollectionType,
                    collection_id: mockCollectionId
                }
            } as LayoutLoadEvent)
        ).rejects.toThrow('Collection');
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

        load({
            params: {
                dataset_id: mockDatasetId,
                collection_type: 'image', // Wrong type
                collection_id: mockCollectionId
            }
        } as LayoutLoadEvent);

        // Give it a moment to call goto
        await new Promise((resolve) => setTimeout(resolve, 0));

        expect(gotoMock).toHaveBeenCalledWith(
            routeHelpers.toCollectionHome(mockDatasetId, 'video', mockCollectionId)
        );
    });

    it('should throw error when collection does not belong to dataset', async () => {
        vi.mocked(readCollection).mockResolvedValueOnce({
            data: mockCollection,
            request: undefined,
            response: undefined
        });

        // Mock readCollectionHierarchy to return only the dataset, not the collection
        vi.mocked(readCollectionHierarchy).mockResolvedValue({
            data: [mockDataset], // Collection not in hierarchy
            request: undefined,
            response: undefined
        });

        await expect(
            load({
                params: {
                    dataset_id: mockDatasetId,
                    collection_type: mockCollectionType,
                    collection_id: mockCollectionId
                }
            } as LayoutLoadEvent)
        ).rejects.toThrow('does not belong to dataset');
    });

    it('should throw error when hierarchy fetch fails', async () => {
        vi.mocked(readCollection).mockResolvedValueOnce({
            data: mockCollection,
            request: undefined,
            response: undefined
        });

        // Mock readCollectionHierarchy to throw an error
        vi.mocked(readCollectionHierarchy).mockRejectedValue(new Error('Hierarchy fetch failed'));

        await expect(
            load({
                params: {
                    dataset_id: mockDatasetId,
                    collection_type: mockCollectionType,
                    collection_id: mockCollectionId
                }
            } as LayoutLoadEvent)
        ).rejects.toThrow('Error loading collection hierarchy');
    });
});
