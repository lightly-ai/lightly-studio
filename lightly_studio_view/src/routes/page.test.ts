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
    it('should redirect to the most recent root dataset', async () => {
        const spyRedirect = vi.spyOn(svelteKit, 'redirect');
        const spyReadDatasets = vi.spyOn(sdkModule, 'readCollections').mockResolvedValue({
            data: [
                {
                    collection_id: '1',
                    name: 'Old Dataset',
                    parent_collection_id: null,
                    created_at: new Date('2023-01-01'),
                    updated_at: new Date('2023-01-02')
                },
                {
                    collection_id: '2',
                    name: 'Recent Dataset',
                    parent_collection_id: null,
                    created_at: new Date('2023-02-01'),
                    updated_at: new Date('2023-02-02')
                }
            ],
            request: undefined,
            response: undefined
        });

        await expect(load()).resolves.toBeUndefined();

        expect(spyReadDatasets).toHaveBeenCalled();

        expect(spyRedirect).toHaveBeenCalledWith(
            307,
            `/datasets/2` // Should redirect to the most recent root dataset
        );
    });

    it('should filter out child datasets and only consider root datasets', async () => {
        const spyRedirect = vi.spyOn(svelteKit, 'redirect');
        const spyReadDatasets = vi.spyOn(sdkModule, 'readCollections').mockResolvedValue({
            data: [
                {
                    collection_id: '1',
                    name: 'Root Dataset',
                    parent_collection_id: null,
                    created_at: new Date('2023-01-01'),
                    updated_at: new Date('2023-01-02')
                },
                {
                    collection_id: '2',
                    name: 'Child Dataset',
                    parent_collection_id: '1',
                    created_at: new Date('2023-02-01'),
                    updated_at: new Date('2023-02-02')
                }
            ],
            request: undefined,
            response: undefined
        });

        await expect(load()).resolves.toBeUndefined();

        expect(spyReadDatasets).toHaveBeenCalled();

        expect(spyRedirect).toHaveBeenCalledWith(
            307,
            `/datasets/1` // Should redirect to root dataset, not child
        );
    });

    it('should throw error when readCollections fails', async () => {
        const error = new Error('Not Found');
        vi.spyOn(sdkModule, 'readCollections').mockRejectedValue(error);

        await expect(load()).rejects.toThrow(error);
    });

    it('should throw error when no datasets found', async () => {
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

    it('should throw error when no root datasets exist', async () => {
        vi.spyOn(sdkModule, 'readCollections').mockResolvedValue({
            data: [
                {
                    dataset_id: '1',
                    name: 'Child Dataset 1',
                    parent_collection_id: 'some-parent',
                    created_at: new Date('2023-01-01'),
                    updated_at: new Date('2023-01-02')
                },
                {
                    dataset_id: '2',
                    name: 'Child Dataset 2',
                    parent_collection_id: 'some-parent',
                    created_at: new Date('2023-02-01'),
                    updated_at: new Date('2023-02-02')
                }
            ],
            request: undefined,
            response: undefined
        });

        await expect(load()).rejects.toThrow('No valid root dataset found');
    });
});
