import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('$app/environment', () => ({
    browser: true
}));

vi.mock('$lib/version.json', () => ({
    version: '1.2.3'
}));

const INSTALL_ID = '0199f1a2-b775-76b8-9b09-c2fd260c67c1';
// A distinct id posthog generates for an anonymous visitor, before anyone identifies.
const ANONYMOUS_ID = '0198aaaa-0000-7000-8000-000000000000';
const CONFIG = {
    install_id: INSTALL_ID,
    posthog_key: 'prod-key',
    posthog_host: 'https://eu.i.posthog.com'
};

const mockInit = vi.fn();
const mockCapture = vi.fn();
const mockRegister = vi.fn();
const mockIdentify = vi.fn();
const mockGetDistinctId = vi.fn();

vi.mock('posthog-js', () => ({
    default: {
        init: (...args: unknown[]) => mockInit(...args),
        capture: (...args: unknown[]) => mockCapture(...args),
        register: (...args: unknown[]) => mockRegister(...args),
        identify: (...args: unknown[]) => mockIdentify(...args),
        get_distinct_id: () => mockGetDistinctId()
    }
}));

// Mocked at the module registry rather than spied on, so it survives the vi.resetModules() the
// tests below need to get an uninitialized hook.
const mockGetFeatures = vi.fn();
const mockGetAnalyticsConfig = vi.fn();

vi.mock('$lib/api/lightly_studio_local/sdk.gen', () => ({
    getFeatures: (...args: unknown[]) => mockGetFeatures(...args),
    getAnalyticsConfig: (...args: unknown[]) => mockGetAnalyticsConfig(...args)
}));

describe('usePostHog', () => {
    beforeEach(() => {
        mockInit.mockClear();
        mockCapture.mockClear();
        mockRegister.mockClear();
        mockIdentify.mockClear();
        mockGetDistinctId.mockReset();
        // Nobody identified yet is the common OSS case: posthog holds an anonymous id.
        mockGetDistinctId.mockReturnValue(ANONYMOUS_ID);
        mockGetFeatures.mockReset();
        mockGetFeatures.mockResolvedValue({ data: ['analytics'] });
        mockGetAnalyticsConfig.mockReset();
        mockGetAnalyticsConfig.mockResolvedValue({ data: CONFIG });
    });

    it('should initialize PostHog with correct configuration', async () => {
        const { init } = await freshPostHog();
        await init();

        expect(mockInit).toHaveBeenCalledWith('prod-key', {
            api_host: 'https://eu.i.posthog.com',
            person_profiles: 'identified_only',
            capture_pageview: true,
            capture_pageleave: true,
            capture_exceptions: true
        });
        expect(mockRegister).toHaveBeenCalledWith({ app_version: '1.2.3' });
    });

    it('should identify with the backend install id when the visitor is anonymous', async () => {
        mockGetDistinctId.mockReturnValue(ANONYMOUS_ID);

        const { init } = await freshPostHog();
        await init();

        expect(mockIdentify).toHaveBeenCalledWith(INSTALL_ID);
    });

    it('should keep an enterprise user identified by email instead of the install id', async () => {
        mockGetDistinctId.mockReturnValue('user@lightly.ai');

        const { init } = await freshPostHog();
        await init();

        expect(mockInit).toHaveBeenCalled();
        expect(mockIdentify).not.toHaveBeenCalled();
    });

    it('should reconcile a stale install id to the current one', async () => {
        mockGetDistinctId.mockReturnValue('0199aaaa-b775-76b8-9b09-000000000000');

        const { init } = await freshPostHog();
        await init();

        expect(mockIdentify).toHaveBeenCalledWith(INSTALL_ID);
    });

    it('should not initialize when the config request fails', async () => {
        mockGetAnalyticsConfig.mockRejectedValue(new Error('API Error'));

        const { init } = await freshPostHog();
        await init();

        expect(mockInit).not.toHaveBeenCalled();
        expect(mockIdentify).not.toHaveBeenCalled();
    });

    it('should report to the project the backend picks', async () => {
        mockGetAnalyticsConfig.mockResolvedValue({
            data: { ...CONFIG, posthog_key: 'dev-key' }
        });

        await (await freshPostHog()).init();

        expect(mockInit).toHaveBeenCalledWith('dev-key', expect.anything());
    });

    it('should track events after initialization', async () => {
        const { init, trackEvent } = await freshPostHog();
        await init();
        trackEvent('test_event', { test: 'data' });

        expect(mockCapture).toHaveBeenCalledWith('test_event', { test: 'data' });
    });

    it('should initialize once when init is called twice concurrently', async () => {
        const { init } = await freshPostHog();

        await Promise.all([init(), init()]);

        expect(mockInit).toHaveBeenCalledTimes(1);
    });

    it('should not initialize when the backend reports analytics as off', async () => {
        mockGetFeatures.mockResolvedValue({ data: [] });

        await (await freshPostHog()).init();

        expect(mockInit).not.toHaveBeenCalled();
    });

    it('should request the config while the feature flags are still in flight', async () => {
        // Serializing the two requests doubles the window in which events are dropped.
        let resolveFeatures: (features: unknown) => void = () => {};
        mockGetFeatures.mockReturnValue(new Promise((resolve) => (resolveFeatures = resolve)));

        const { init } = await freshPostHog();
        const initialized = init();
        await Promise.resolve();

        expect(mockGetAnalyticsConfig).toHaveBeenCalled();

        resolveFeatures({ data: ['analytics'] });
        await initialized;
        expect(mockInit).toHaveBeenCalled();
    });

    it('should not initialize when the features request fails', async () => {
        mockGetFeatures.mockRejectedValue(new Error('API Error'));

        await (await freshPostHog()).init();

        expect(mockInit).not.toHaveBeenCalled();
    });
});

/** Load a hook that has not been initialized yet, since the flag is module scoped. */
const freshPostHog = async () => {
    vi.resetModules();
    return (await import('./usePostHog')).usePostHog();
};
