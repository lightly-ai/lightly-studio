import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('$app/environment', () => ({
    browser: true
}));

vi.mock('$env/static/public', () => ({
    PUBLIC_POSTHOG_KEY: 'prod-key',
    PUBLIC_POSTHOG_DEV_KEY: 'dev-key',
    PUBLIC_POSTHOG_HOST: 'https://eu.i.posthog.com'
}));

vi.mock('$lib/version.json', () => ({
    version: '1.2.3'
}));

const mockInit = vi.fn();
const mockCapture = vi.fn();
const mockRegister = vi.fn();
const mockIdentify = vi.fn();

vi.mock('posthog-js', () => ({
    default: {
        init: (...args: unknown[]) => mockInit(...args),
        capture: (...args: unknown[]) => mockCapture(...args),
        register: (...args: unknown[]) => mockRegister(...args),
        identify: (...args: unknown[]) => mockIdentify(...args)
    }
}));

// Mocked at the module registry rather than spied on, so it survives the vi.resetModules() the
// tests below need to get an uninitialized hook.
const mockGetAnalyticsConfig = vi.fn();

vi.mock('$lib/api/lightly_studio_local/sdk.gen', () => ({
    getAnalyticsConfig: (...args: unknown[]) => mockGetAnalyticsConfig(...args)
}));

const enabledConfig = {
    data: { enabled: true, distinct_id: 'install-id', user_cohort: 'user' }
};

describe('usePostHog', () => {
    beforeEach(() => {
        mockInit.mockClear();
        mockCapture.mockClear();
        mockRegister.mockClear();
        mockIdentify.mockClear();
        mockGetAnalyticsConfig.mockReset();
        mockGetAnalyticsConfig.mockResolvedValue(enabledConfig);
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

    it('should identify with the installation id and cohort reported by the backend', async () => {
        mockGetAnalyticsConfig.mockResolvedValue({
            data: { enabled: true, distinct_id: 'install-id', user_cohort: 'staff' }
        });

        await (await freshPostHog()).init();

        expect(mockIdentify).toHaveBeenCalledWith('install-id', { user_cohort: 'staff' });
    });

    it('should not initialize when the backend reports analytics as off', async () => {
        mockGetAnalyticsConfig.mockResolvedValue({
            data: { enabled: false, distinct_id: null, user_cohort: null }
        });

        await (await freshPostHog()).init();

        expect(mockInit).not.toHaveBeenCalled();
    });

    it('should not initialize when the config request fails', async () => {
        mockGetAnalyticsConfig.mockRejectedValue(new Error('API Error'));

        await (await freshPostHog()).init();

        expect(mockInit).not.toHaveBeenCalled();
    });
});

/** Load a hook that has not been initialized yet, since the flag is module scoped. */
const freshPostHog = async () => {
    vi.resetModules();
    return (await import('./usePostHog')).usePostHog();
};
