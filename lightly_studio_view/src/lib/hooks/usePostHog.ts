import posthog from 'posthog-js';
import { browser } from '$app/environment';
import { version } from '$lib/version.json';
import { getAnalyticsConfig } from '$lib/api/lightly_studio_local/sdk.gen';
// Imported by its own path: $lib/hooks re-exports usePostHog, so going through the barrel would
// make the two modules import each other.
import { useFeatureFlags } from '$lib/hooks/useFeatureFlags/useFeatureFlags';
import { get } from 'svelte/store';

// The backend reports this only while LIGHTLY_STUDIO_ANALYTICS_ENABLED is set, so one variable
// opts out of tracking in both the Python package and here.
const ANALYTICS_FEATURE = 'analytics';

let initialized = false;

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
    /**
     * Start PostHog, unless the backend reports that usage tracking is switched off.
     *
     * Resolves once the decision is made. Events fired before then are dropped by trackEvent().
     */
    const init = async () => {
        if (!browser || initialized) return;

        // Started before the flags, which it does not depend on, since every event fired until
        // both land is dropped. Requesting it with tracking switched off is safe: the endpoint
        // refuses before it writes an install id.
        const configResponse = getAnalyticsConfig().catch((error: unknown) => {
            console.warn('Failed to read the analytics configuration', error);
            return undefined;
        });

        // A failed request leaves the flags empty, so a backend that cannot be reached is never
        // tracked against.
        const { featureFlags, ready } = useFeatureFlags();
        await ready;
        if (!get(featureFlags).includes(ANALYTICS_FEATURE)) return;

        // Only the backend can tell a checkout from a released package, so it picks the
        // project. Without a key there is nothing to fall back to.
        const config = (await configResponse)?.data;
        if (!config) return;
        // Re-check: the awaits above let a second concurrent caller reach this point too.
        if (initialized) return;

        posthog.init(config.posthog_key, {
            api_host: config.posthog_host,
            person_profiles: 'identified_only',
            capture_pageview: true,
            capture_pageleave: true,
            capture_exceptions: true
        });
        posthog.register({ app_version: version });
        initialized = true;

        // One distinct id per install, shared with the Python SDK, instead of two.
        posthog.identify(config.install_id);
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
        if (!initialized) return;
        posthog.capture(eventName, properties);
    };

    return {
        init,
        trackEvent
    };
};
