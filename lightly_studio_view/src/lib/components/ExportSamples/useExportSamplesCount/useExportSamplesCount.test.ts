import { client } from '$lib/services/dataset';
import { get } from 'svelte/store';
import { describe, expect, it, vi } from 'vitest';
import { useExportSamplesCount } from './useExportSamplesCount';

const defaultProps: Parameters<typeof useExportSamplesCount>[0] = {
    dataset_id: 'test-dataset',
    includeFilter: {
        tag_ids: ['tag1', 'tag2']
    }
} as const;

describe('useExportStats', () => {
    beforeEach(vi.resetAllMocks);

    it('should call samples_paths endpoint', () => {
        const mockedSpy = vi.spyOn(client, 'POST').mockResolvedValueOnce({ data: 0 });
        useExportSamplesCount(defaultProps);
        expect(mockedSpy).toHaveBeenCalledWith('/api/datasets/{dataset_id}/export/stats', {
            body: {
                include: defaultProps.includeFilter,
                exclude: undefined
            },
            params: {
                path: {
                    dataset_id: 'test-dataset'
                }
            }
        });
    });

    it('should reflect loading state', async () => {
        const expectedCount = 42;
        vi.spyOn(client, 'POST').mockResolvedValueOnce({ data: expectedCount });
        const { isLoading, count, error } = useExportSamplesCount(defaultProps);

        // Initial state
        expect(get(isLoading)).toBe(true);
        expect(get(count)).toBe(0);
        expect(get(error)).toBeUndefined();

        await vi.waitFor(() => {
            expect(get(isLoading)).toBe(false);
            expect(get(count)).toBe(expectedCount);
            expect(get(error)).toBeUndefined();
        });
    });

    it('should handle errors', async () => {
        const errorMessage = 'API Error';
        vi.spyOn(client, 'POST').mockRejectedValueOnce(new Error(errorMessage));

        const { isLoading, count, error } = useExportSamplesCount(defaultProps);

        // // Wait for error to be displayed
        await vi.waitFor(() => {
            expect(get(isLoading)).toBe(false);
            expect(get(count)).toBe(0);
            expect(get(error)).toBe(errorMessage);
        });
    });
});
