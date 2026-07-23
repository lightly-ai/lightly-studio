import { get, writable } from 'svelte/store';
import { usePostHog } from '$lib/hooks/usePostHog';
import { useGlobalStorage } from '$lib/hooks/useGlobalStorage';

const isExportDialogOpen = writable(false);
const downloadedInSession = writable(false);

interface OpenExportDialogParams {
    collectionId: string;
}

interface CloseExportDialogParams {
    collectionId: string;
    exportFormat: string;
}

export function useExportDialog() {
    const { trackEvent } = usePostHog();
    const { filteredSampleCount } = useGlobalStorage();

    const openExportDialog = ({ collectionId }: OpenExportDialogParams) => {
        if (get(isExportDialogOpen)) return;
        downloadedInSession.set(false);
        isExportDialogOpen.set(true);
        trackEvent('export_dialog_opened', {
            collection_id: collectionId,
            filtered_sample_count: get(filteredSampleCount)
        });
    };

    const closeExportDialog = ({ collectionId, exportFormat }: CloseExportDialogParams) => {
        if (!get(isExportDialogOpen)) return;
        if (!get(downloadedInSession)) {
            trackEvent('export_dialog_dismissed', {
                collection_id: collectionId,
                export_format: exportFormat
            });
        }
        isExportDialogOpen.set(false);
    };

    const markDownloadClicked = () => {
        downloadedInSession.set(true);
    };

    return {
        isExportDialogOpen,
        openExportDialog,
        closeExportDialog,
        markDownloadClicked
    };
}
