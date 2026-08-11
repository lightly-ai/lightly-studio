import { getLaunchSource } from '$lib/api/lightly_studio_local/sdk.gen';
import { LaunchSource } from '$lib/api/lightly_studio_local';
import { usePostHog } from '$lib/hooks/usePostHog';

// Holds the launch ID of the most recently reported launch, so a reload or a second tab does not
// count the same `lightly-studio quickstart` run twice.
const REPORTED_LAUNCH_ID_KEY = 'lightlyStudio_reportedLaunchId';

interface UseLaunchSourceReturn {
    trackLaunchSource: () => Promise<void>;
}

/**
 * Reports how the running LightlyStudio app was started to PostHog.
 *
 * Registers `launch_source` as a session property so every later event in the session can be
 * segmented by entry point, and captures `quickstart_launched` once per run of the
 * `lightly-studio quickstart` command.
 */
export const useLaunchSource = (): UseLaunchSourceReturn => {
    const { trackEvent, registerSessionProperties } = usePostHog();

    const trackLaunchSource = async () => {
        try {
            const { data } = await getLaunchSource();
            if (!data) return;

            registerSessionProperties({ launch_source: data.launch_source });

            if (data.launch_source !== LaunchSource.QUICKSTART) return;
            if (readReportedLaunchId() === data.launch_id) return;

            markLaunchReported(data.launch_id);
            trackEvent('quickstart_launched', { launch_id: data.launch_id });
        } catch {
            // Analytics must never break app startup.
        }
    };

    return {
        trackLaunchSource
    };
};

/**
 * Read the last reported launch ID.
 *
 * Returns null when storage is unavailable, so a launch is reported rather than silently dropped.
 */
const readReportedLaunchId = (): string | null => {
    if (typeof localStorage === 'undefined') return null;
    try {
        return localStorage.getItem(REPORTED_LAUNCH_ID_KEY);
    } catch (e) {
        console.warn(`Failed to read ${REPORTED_LAUNCH_ID_KEY} from localStorage`, e);
        return null;
    }
};

const markLaunchReported = (launchId: string) => {
    if (typeof localStorage === 'undefined') return;
    try {
        localStorage.setItem(REPORTED_LAUNCH_ID_KEY, launchId);
    } catch (e) {
        console.warn(`Failed to write ${REPORTED_LAUNCH_ID_KEY} to localStorage`, e);
    }
};
