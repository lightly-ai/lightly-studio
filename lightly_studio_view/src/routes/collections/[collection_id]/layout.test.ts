import { readCollection } from '$lib/api/lightly_studio_local/sdk.gen';
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
        const mockCollectionId = 'test-collection-id';

        beforeEach(() => {
            vi.clearAllMocks();
            vi.mocked(readCollection).mockResolvedValue({
                data: {
                    collection_id: mockCollectionId,
                    name: 'Test Collection'
                } as CollectionTable,
                request: undefined,
                response: undefined
            });
        });

        it('should load collection and return data', async () => {
            const result = await load({
                params: { collection_id: mockCollectionId }
            } as LayoutLoadEvent);

            expect(result.collectionId).toBe(mockCollectionId);
            expect(result.collection).toBeDefined();
            expect(result.globalStorage).toBeDefined();
        });

        it('should redirect when collection not found', async () => {
            vi.mocked(readCollection).mockRejectedValue(new Error('Not found'));

            try {
                await load({ params: { collection_id: 'invalid' } } as LayoutLoadEvent);
                expect.fail('Should have thrown redirect');
            } catch (error) {
                expect(error.status).toBe(307);
                expect(error.location).toBe(routeHelpers.toHome());
            }
        });
    });
});
