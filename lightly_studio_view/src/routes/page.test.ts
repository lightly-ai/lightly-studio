// src/routes/+page.test.ts
import { load } from './+page';
import { vi } from 'vitest';
import * as sdkModule from '$lib/api/lightly_studio_local/sdk.gen';
import * as svelteKit from '@sveltejs/kit';

vi.mock('@sveltejs/kit', () => {
    return {
        redirect: vi.fn() // Mock the redirect function
    };
});

afterEach(() => {
    vi.clearAllMocks();
});

describe('load function', () => {
    it('should redirect to the most recent root collection', async () => {
        const spyRedirect = vi.spyOn(svelteKit, 'redirect');
        const spyReadCollections = vi.spyOn(sdkModule, 'readCollections').mockResolvedValue({
            data: [
                {
                    collection_id: '1',
                    name: 'Old Collection',
                    parent_collection_id: null,
                    created_at: new Date('2023-01-01'),
                    updated_at: new Date('2023-01-02')
                },
                {
                    collection_id: '2',
                    name: 'Recent Collection',
                    parent_collection_id: null,
                    created_at: new Date('2023-02-01'),
                    updated_at: new Date('2023-02-02')
                }
            ],
            request: undefined,
            response: undefined
        });

        await expect(load()).resolves.toBeUndefined();

        expect(spyReadCollections).toHaveBeenCalled();

        expect(spyRedirect).toHaveBeenCalledWith(
            307,
            `/datasets/2/image/2` // Should redirect to the most recent root collection using new route structure
        );
    });

    it('should filter out child collections and only consider root collections', async () => {
        const spyRedirect = vi.spyOn(svelteKit, 'redirect');
        const spyReadCollections = vi.spyOn(sdkModule, 'readCollections').mockResolvedValue({
            data: [
                {
                    collection_id: '1',
                    name: 'Root Collection',
                    parent_collection_id: null,
                    created_at: new Date('2023-01-01'),
                    updated_at: new Date('2023-01-02')
                },
                {
                    collection_id: '2',
                    name: 'Child Collection',
                    parent_collection_id: '1',
                    created_at: new Date('2023-02-01'),
                    updated_at: new Date('2023-02-02')
                }
            ],
            request: undefined,
            response: undefined
        });

        await expect(load()).resolves.toBeUndefined();

        expect(spyReadCollections).toHaveBeenCalled();

        expect(spyRedirect).toHaveBeenCalledWith(
            307,
            `/datasets/1/image/1` // Should redirect to root collection, not child, using new route structure
        );
    });

    it('should throw error when readCollections fails', async () => {
        const error = new Error('Not Found');
        vi.spyOn(sdkModule, 'readCollections').mockRejectedValue(error);

        await expect(load()).rejects.toThrow(error);
    });

    it('should throw error when no collections found', async () => {
        vi.spyOn(sdkModule, 'readCollections').mockResolvedValue({
            data: [],
            request: undefined,
            response: undefined
        });

        await expect(load()).rejects.toThrow('No datasets found');
    });

    it('should throw error when data is undefined', async () => {
        vi.spyOn(sdkModule, 'readCollections').mockResolvedValue({
            data: undefined,
            request: undefined,
            response: undefined
        });

        await expect(load()).rejects.toThrow('No datasets found');
    });

    it('should throw error when no root collections exist', async () => {
        vi.spyOn(sdkModule, 'readCollections').mockResolvedValue({
            data: [
                {
                    collection_id: '1',
                    name: 'Child Collection 1',
                    parent_collection_id: 'some-parent',
                    created_at: new Date('2023-01-01'),
                    updated_at: new Date('2023-01-02')
                },
                {
                    collection_id: '2',
                    name: 'Child Collection 2',
                    parent_collection_id: 'some-parent',
                    created_at: new Date('2023-02-01'),
                    updated_at: new Date('2023-02-02')
                }
            ],
            request: undefined,
            response: undefined
        });

        await expect(load()).rejects.toThrow('No valid root collection found');
    });
});
