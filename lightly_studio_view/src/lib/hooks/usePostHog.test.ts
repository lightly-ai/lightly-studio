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

const mockInit = vi.fn();
const mockCapture = vi.fn();

vi.mock('posthog-js', () => ({
    default: {
        init: (...args: unknown[]) => mockInit(...args),
        capture: (...args: unknown[]) => mockCapture(...args)
    }
}));

describe('usePostHog', () => {
    beforeEach(() => {
        mockInit.mockClear();
        mockCapture.mockClear();
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
    });

    it('should track events after initialization', () => {
        const { init, trackEvent } = usePostHog();
        init();
        trackEvent('test_event', { test: 'data' });

        expect(mockCapture).toHaveBeenCalledWith('test_event', { test: 'data' });
    });
});
