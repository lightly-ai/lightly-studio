import { readDataset } from '$lib/api/lightly_studio_local/sdk.gen';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { LayoutLoadEvent } from './$types';
import { load } from './+layout';
import { routeHelpers } from '../../../lib/routes';
import type { CollectionTable } from '../../../lib/api/lightly_studio_local';

// Mock the service imports
vi.mock('$lib/services/loadDimensionBounds');
vi.mock('$lib/api/lightly_studio_local/sdk.gen');
vi.mock('$lib/components/TagsMenu', () => ({
    useTags: vi.fn().mockResolvedValue({
        tags: [],
        tagsSelected: [],
        tagSelectionToggle: vi.fn()
    })
}));

describe('+layout.ts', () => {
    describe('+layout.ts', () => {
        const mockDatasetId = 'test-dataset-id';

        beforeEach(() => {
            vi.clearAllMocks();
            vi.mocked(readDataset).mockResolvedValue({
                data: {
                    dataset_id: mockDatasetId,
                    name: 'Test Dataset'
                } as CollectionTable,
                request: undefined,
                response: undefined
            });
        });

        it('should load dataset and return data', async () => {
            const result = await load({
                params: { dataset_id: mockDatasetId }
            } as LayoutLoadEvent);

            expect(result.datasetId).toBe(mockDatasetId);
            expect(result.dataset).toBeDefined();
            expect(result.globalStorage).toBeDefined();
        });

        it('should redirect when dataset not found', async () => {
            vi.mocked(readDataset).mockRejectedValue(new Error('Not found'));

            try {
                await load({ params: { dataset_id: 'invalid' } } as LayoutLoadEvent);
                expect.fail('Should have thrown redirect');
            } catch (error) {
                expect(error.status).toBe(307);
                expect(error.location).toBe(routeHelpers.toHome());
            }
        });
    });
});
