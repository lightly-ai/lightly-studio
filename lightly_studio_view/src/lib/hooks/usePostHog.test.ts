import { beforeEach, describe, expect, it, vi } from 'vitest';
import { usePostHog } from './usePostHog';

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
const mockRegisterForSession = vi.fn();

vi.mock('posthog-js', () => ({
    default: {
        init: (...args: unknown[]) => mockInit(...args),
        capture: (...args: unknown[]) => mockCapture(...args),
        register: (...args: unknown[]) => mockRegister(...args),
        register_for_session: (...args: unknown[]) => mockRegisterForSession(...args)
    }
}));

describe('usePostHog', () => {
    beforeEach(() => {
        mockInit.mockClear();
        mockCapture.mockClear();
        mockRegister.mockClear();
        mockRegisterForSession.mockClear();
    });

    it('should initialize PostHog with correct configuration', () => {
        const { init } = usePostHog();
        init();

        expect(mockInit).toHaveBeenCalledWith('prod-key', {
            api_host: 'https://eu.i.posthog.com',
            person_profiles: 'identified_only',
            capture_pageview: true,
            capture_pageleave: true,
            capture_exceptions: true
        });
        expect(mockRegister).toHaveBeenCalledWith({ app_version: '1.2.3' });
    });

    it('should track events after initialization', () => {
        const { init, trackEvent } = usePostHog();
        init();
        trackEvent('test_event', { test: 'data' });

        expect(mockCapture).toHaveBeenCalledWith('test_event', { test: 'data' });
    });

    it('should register session properties after initialization', () => {
        const { init, registerSessionProperties } = usePostHog();
        init();
        registerSessionProperties({ launch_source: 'quickstart' });

        expect(mockRegisterForSession).toHaveBeenCalledWith({ launch_source: 'quickstart' });
    });

    it('should ignore session properties before initialization', async () => {
        // The initialized flag is module scoped, so reload the module to get an uninitialized one.
        vi.resetModules();
        const { usePostHog: useFreshPostHog } = await import('./usePostHog');

        useFreshPostHog().registerSessionProperties({ launch_source: 'quickstart' });

        expect(mockRegisterForSession).not.toHaveBeenCalled();
    });
});
