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
    it('should redirect to the dataset path', async () => {
        const mockDatasets = [
            {
                dataset_id: '1',
                name: 'Test Dataset 1',
                created_at: new Date('2023-01-01'),
                updated_at: new Date('2023-01-02')
            },
            {
                dataset_id: '2',
                name: 'Test Dataset 2',
                created_at: new Date('2023-02-01'),
                updated_at: new Date('2023-02-02')
            }
        ];
        const spyRedirect = vi.spyOn(svelteKit, 'redirect');
        const spyLoadLastDatasets = vi.spyOn(sdkModule, 'readDatasets').mockResolvedValue({
            data: mockDatasets,
            request: undefined,
            response: undefined
        });

        await expect(load()).resolves.toBeUndefined();

        expect(spyLoadLastDatasets).toHaveBeenCalled();

        expect(spyRedirect).toHaveBeenCalledWith(
            307,
            `/datasets/2/samples` // Should redirect to the most recent dataset (dataset_id: '2')
        );
    });

    it('should throw error when readDatasets fails', async () => {
        const error = new Error('Not Found');
        vi.spyOn(sdkModule, 'readDatasets').mockRejectedValue(error);

        await expect(load()).rejects.toThrow(error);
    });

    it('should throw error when no datasets found', async () => {
        vi.spyOn(sdkModule, 'readDatasets').mockResolvedValue({
            data: [],
            request: undefined,
            response: undefined
        });

        await expect(load()).rejects.toThrow('No datasets found');
    });
});
