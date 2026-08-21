import posthog from 'posthog-js';
import { browser } from '$app/environment';
import {
    PUBLIC_POSTHOG_KEY,
    PUBLIC_POSTHOG_DEV_KEY,
    PUBLIC_POSTHOG_HOST
} from '$env/static/public';
import { version } from '$lib/version.json';
// Imported by its own path: $lib/hooks re-exports usePostHog, so going through the barrel would
// make the two modules import each other.
import { useAnalyticsConfig } from '$lib/hooks/useAnalyticsConfig/useAnalyticsConfig';
import { get } from 'svelte/store';

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

        // A failed request leaves the config empty, so a backend that cannot be reached is never
        // tracked against. LIGHTLY_STUDIO_ANALYTICS_ENABLED decides there, so one variable opts
        // out of tracking in both the Python package and here.
        const { config, ready } = useAnalyticsConfig();
        await ready;
        const analyticsConfig = get(config);
        if (!analyticsConfig?.enabled) return;
        // Re-check: concurrent callers both get past the guard above before this resolves.
        if (initialized) return;

        const apiKey = PUBLIC_POSTHOG_KEY || PUBLIC_POSTHOG_DEV_KEY;
        const apiHost = PUBLIC_POSTHOG_HOST || 'https://eu.i.posthog.com';

        if (!apiKey) {
            console.warn('PostHog API key not configured');
            return;
        }

        posthog.init(apiKey, {
            api_host: apiHost,
            person_profiles: 'identified_only',
            capture_pageview: true,
            capture_pageleave: true,
            capture_exceptions: true
        });
        posthog.register({ app_version: version });

        // Report against the installation ID the Python package uses, so backend and browser
        // events belong to one person rather than two, with the cohort on that person.
        if (analyticsConfig.distinct_id) {
            posthog.identify(analyticsConfig.distinct_id, {
                user_cohort: analyticsConfig.user_cohort
            });
        }

        initialized = true;
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
