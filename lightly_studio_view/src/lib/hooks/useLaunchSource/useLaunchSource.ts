import { getLaunchSource } from '$lib/api/lightly_studio_local/sdk.gen';
import { LaunchSource } from '$lib/api/lightly_studio_local';
import { usePostHog } from '$lib/hooks/usePostHog';

/**
 * Reports how the running LightlyStudio app was started to PostHog.
 *
 * Registers `launch_source` as a super property so every later event in the session can be
 * segmented by entry point, and captures a one-off event when the app came from the
 * `lightly-studio quickstart` command.
 */
export const useLaunchSource = () => {
    const { trackEvent, registerSuperProperties } = usePostHog();

    const trackLaunchSource = async () => {
        try {
            const { data } = await getLaunchSource();
            if (!data) return;

            registerSuperProperties({ launch_source: data.launch_source });
            if (data.launch_source === LaunchSource.QUICKSTART) {
                trackEvent('quickstart_launched');
            }
        } catch {
            // Analytics must never break app startup.
        }
    };

    return {
        trackLaunchSource
    };
};
