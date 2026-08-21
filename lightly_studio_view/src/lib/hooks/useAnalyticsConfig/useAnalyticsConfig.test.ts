import { get } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAnalyticsConfig } from './useAnalyticsConfig';

const mockGetAnalyticsConfig = vi.fn();

vi.mock('$lib/api/lightly_studio_local/sdk.gen', () => ({
    getAnalyticsConfig: (...args: unknown[]) => mockGetAnalyticsConfig(...args)
}));

const config = { enabled: true, distinct_id: 'install-id', user_cohort: 'staff' };

describe('useAnalyticsConfig', () => {
    beforeEach(() => {
        mockGetAnalyticsConfig.mockReset();
    });

    it('should expose the configuration reported by the backend', async () => {
        mockGetAnalyticsConfig.mockResolvedValue({ data: config });

        const { config: store, ready } = useAnalyticsConfig();
        await ready;

        expect(get(store)).toEqual(config);
    });

    it.each([
        ['the request rejects', () => mockGetAnalyticsConfig.mockRejectedValue(new Error('nope'))],
        // The client resolves with an error rather than rejecting on an HTTP failure.
        [
            'the response carries an error',
            () => mockGetAnalyticsConfig.mockResolvedValue({ error: {} })
        ]
    ])('should leave the configuration empty when %s', async (_name, arrange) => {
        arrange();

        const { config: store, ready } = useAnalyticsConfig();
        await ready;

        expect(get(store)).toBeNull();
    });
});
