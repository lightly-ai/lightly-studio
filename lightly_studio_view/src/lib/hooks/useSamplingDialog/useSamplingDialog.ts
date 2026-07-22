import { writable } from 'svelte/store';
import { usePostHog } from '$lib/hooks';

const isSamplingDialogOpen = writable(false);

interface OpenDialogAnalytics {
    collection_id: string;
    has_active_search: boolean;
}

export function useSamplingDialog() {
    const { trackEvent } = usePostHog();

    const openSamplingDialog = (analytics?: OpenDialogAnalytics) => {
        isSamplingDialogOpen.set(true);
        if (analytics) {
            trackEvent('sampling_dialog_opened', analytics);
        }
    };

    const closeSamplingDialog = () => {
        isSamplingDialogOpen.set(false);
    };

    return {
        isSamplingDialogOpen,
        openSamplingDialog,
        closeSamplingDialog
    };
}
