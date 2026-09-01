import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('$app/environment', () => ({
    browser: true
}));

vi.mock('$lib/version.json', () => ({
    version: '1.2.3'
}));

const INSTALL_ID = '0199f1a2-b775-76b8-9b09-c2fd260c67c1';
const CONFIG = {
    install_id: INSTALL_ID,
    posthog_key: 'prod-key',
    posthog_host: 'https://eu.i.posthog.com'
};

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

    it('should identify with the backend install id after initialization', async () => {
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
