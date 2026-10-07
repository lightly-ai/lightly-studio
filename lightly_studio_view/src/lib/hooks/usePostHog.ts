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
let readyPromise: Promise<boolean> | null = null;

async function startInit(): Promise<boolean> {
    if (!browser || initialized) return initialized;

    const configResponse = getAnalyticsConfig().catch((error: unknown) => {
        console.warn('Failed to read the analytics configuration', error);
        return undefined;
    });

    const { featureFlags, ready } = useFeatureFlags();
    await ready;
    if (!get(featureFlags).includes(ANALYTICS_FEATURE)) return false;

    const config = (await configResponse)?.data;
    if (!config) return false;
    if (initialized) return true;

    posthog.init(config.posthog_key, {
        api_host: config.posthog_host,
        person_profiles: 'identified_only',
        capture_pageview: true,
        capture_pageleave: true,
        capture_exceptions: true
    });
    posthog.register({ app_version: version });
    initialized = true;

    // Only identify with the install_id for non-enterprise.
    // In enterprise, users would already be logged in/identified, and we don't want to
    // overwrite that. Overwriting with the install_id would collapse every logged-in user
    // onto a single install_id.
    const currentId = posthog.get_distinct_id();
    const identifiedAsEnterpriseUser = typeof currentId === 'string' && currentId.includes('@');
    if (!identifiedAsEnterpriseUser) {
        // One distinct id per install, shared with the Python SDK, instead of two.
        posthog.identify(config.install_id);
    }

    return true;
}

/**
 * PostHog analytics hook for tracking user behavior and events.
 *
 * Automatically tracks page views, navigation, and JavaScript errors.
 * Use trackEvent() to capture custom user actions like collection loads, exports, or feature usage.
 *
 * Initialization starts eagerly on first call. Await `ready` to know whether PostHog initialized
 * before firing events that must be attributed (e.g. onboarding steps). `ready` always resolves —
 * it is `true` when PostHog is active, `false` when tracking is disabled or unavailable.
 *
 * @example
 * ```ts
 * const { trackEvent } = usePostHog();
 * trackEvent('collection_loaded', { collection_id: '123', sample_count: 100 });
 * ```
 */
export const usePostHog = () => {
    readyPromise ??= startInit().catch(() => false);

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
        ready: readyPromise,
        trackEvent
    };
};
