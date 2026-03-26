import { browser } from '$app/environment';
import {
    PUBLIC_POSTHOG_KEY,
    PUBLIC_POSTHOG_DEV_KEY,
    PUBLIC_POSTHOG_HOST
} from '$env/static/public';

let initialized = false;
let initPromise: Promise<void> | null = null;
let posthogClient: (typeof import('posthog-js'))['default'] | null = null;

/**
 * PostHog analytics hook for tracking user behavior and events.
 *
 * Automatically tracks page views, navigation, and JavaScript errors.
 * Use trackEvent() to capture custom user actions like collection loads, exports, or feature usage.
 *
 * @example
 * ```ts
 * const { trackEvent } = usePostHog();
 * trackEvent('collection_loaded', { collection_id: '123', sample_count: 100 });
 * ```
 */
export const usePostHog = () => {
    const init = async () => {
        if (!browser || initialized) return;
        if (initPromise) return initPromise;

        const apiKey = PUBLIC_POSTHOG_KEY || PUBLIC_POSTHOG_DEV_KEY;
        const apiHost = PUBLIC_POSTHOG_HOST || 'https://eu.i.posthog.com';

        if (!apiKey) {
            console.warn('PostHog API key not configured');
            return;
        }

        initPromise = import('posthog-js')
            .then(({ default: posthog }) => {
                posthog.init(apiKey, {
                    api_host: apiHost,
                    person_profiles: 'identified_only',
                    capture_pageview: true,
                    capture_pageleave: true,
                    capture_exceptions: true
                });
                posthogClient = posthog;
                initialized = true;
            })
            .finally(() => {
                initPromise = null;
            });

        return initPromise;
    };

    /**
     * Track a custom event with optional properties.
     *
     * Use this to capture user actions like button clicks, feature usage,
     * collection operations, or any meaningful user interaction.
     *
     * @param eventName - Descriptive name for the event (e.g., 'collection_loaded', 'export_triggered')
     * @param properties - Optional metadata about the event (e.g., collection_id, item_count)
     *
     * @example
     * ```ts
     * trackEvent('filter_applied', {
     *   filter_type: 'label',
     *   selected_labels: ['cat', 'dog']
     * });
     * ```
     */
    const trackEvent = (eventName: string, properties?: Record<string, unknown>) => {
        if (!initialized || !posthogClient) return;
        posthogClient.capture(eventName, properties);
    };

    return {
        init,
        trackEvent
    };
};
