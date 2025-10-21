import { vi, describe, it, expect, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { useFeatureFlags } from './useFeatureFlags';
import dataset from '$lib/services/dataset';

describe('useFeatureFlags', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should initialize with empty feature flags', () => {
        const { featureFlags } = useFeatureFlags();
        expect(get(featureFlags)).toEqual([]);
    });

    it('should update feature flags when API call succeeds', async () => {
        const mockFeatures = ['feature1', 'feature2'];
        const mockedGet = vi.spyOn(dataset, 'GET').mockResolvedValueOnce({ data: mockFeatures });

        const { featureFlags } = useFeatureFlags();

        // Wait for the next tick to allow the promise to resolve
        await new Promise((resolve) => setTimeout(resolve, 0));

        expect(get(featureFlags)).toEqual(mockFeatures);
        expect(mockedGet).toHaveBeenCalledWith('/api/features');
    });

    it('should handle API call failure gracefully', async () => {
        const _error: Error = new Error('API Error');
        const mockedGet = vi.spyOn(dataset, 'GET').mockRejectedValueOnce(_error);

        const { featureFlags, error } = useFeatureFlags();

        // Wait for the next tick to allow the promise to resolve
        await new Promise((resolve) => setTimeout(resolve, 0));

        expect(get(featureFlags)).toEqual([]);
        expect(get(error)).toEqual(_error);
        expect(mockedGet).toHaveBeenCalledWith('/api/features');
    });
});
