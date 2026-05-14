import { vi, describe, it, expect, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { useFeatureFlags } from './useFeatureFlags';
import * as sdkModule from '$lib/api/lightly_studio_local/sdk.gen';

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
        const spy = vi.spyOn(sdkModule, 'getFeatures').mockResolvedValueOnce({
            data: mockFeatures,
            request: new Request('http://localhost'),
            response: new Response()
        });

        const { featureFlags } = useFeatureFlags();

        // Wait for the next tick to allow the promise to resolve
        await new Promise((resolve) => setTimeout(resolve, 0));

        expect(get(featureFlags)).toEqual(mockFeatures);
        expect(spy).toHaveBeenCalled();
    });

    it('should handle API call failure gracefully', async () => {
        const _error: Error = new Error('API Error');
        const spy = vi.spyOn(sdkModule, 'getFeatures').mockRejectedValueOnce(_error);

        const { featureFlags, error } = useFeatureFlags();

        // Wait for the next tick to allow the promise to resolve
        await new Promise((resolve) => setTimeout(resolve, 0));

        expect(get(featureFlags)).toEqual([]);
        expect(get(error)).toEqual(_error);
        expect(spy).toHaveBeenCalled();
    });
});
