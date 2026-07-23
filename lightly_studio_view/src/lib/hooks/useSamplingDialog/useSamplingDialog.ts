import { get, writable } from 'svelte/store';
import { usePostHog } from '$lib/hooks';

const isSamplingDialogOpen = writable(false);
const wasSubmitted = writable(false);

interface OpenDialogAnalytics extends Record<string, unknown> {
    collection_id: string;
    filtered_sample_count: number;
}

interface CloseDialogAnalytics extends Record<string, unknown> {
    collection_id: string;
    strategy_count: number;
}

export function useSamplingDialog() {
    const { trackEvent } = usePostHog();

    const openSamplingDialog = (analytics?: OpenDialogAnalytics) => {
        wasSubmitted.set(false);
        isSamplingDialogOpen.set(true);
        if (analytics) {
            trackEvent('sampling_dialog_opened', analytics);
        }
    };

    const markSubmitted = () => wasSubmitted.set(true);

    const closeSamplingDialog = (analytics?: CloseDialogAnalytics) => {
        if (!get(wasSubmitted) && analytics) {
            trackEvent('sampling_dialog_dismissed', analytics);
        }
        isSamplingDialogOpen.set(false);
    };

    return {
        isSamplingDialogOpen,
        openSamplingDialog,
        closeSamplingDialog,
        markSubmitted
    };
}
