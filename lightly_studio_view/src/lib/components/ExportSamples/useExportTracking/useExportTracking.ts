import { get } from 'svelte/store';
import { useExportDialog } from '$lib/hooks';
import { useGlobalStorage, usePostHog } from '$lib/hooks';

interface UseExportTrackingParams {
    collectionId: string;
}

interface TrackExportDownloadClickedParams {
    exportType: string;
    tagNameToExport: string | null;
    sampleCount: number;
}

interface TrackExportTriggeredParams {
    exportType: string;
    tagNameToExport: string | null;
    sampleCount: number;
    success: boolean;
}

interface UseExportTrackingReturn {
    trackDialogDefaultFormatSet: (exportFormat: string) => void;
    trackFormatSelectOpened: (currentFormat: string) => void;
    trackFormatSelected: (exportFormat: string) => void;
    handleAnnotationDownloadClick: (exportFormat: string) => void;
    trackExportDownloadClicked: (params: TrackExportDownloadClickedParams) => void;
    trackExportTriggered: (params: TrackExportTriggeredParams) => void;
}

export function useExportTracking({
    collectionId
}: UseExportTrackingParams): UseExportTrackingReturn {
    const { trackEvent } = usePostHog();
    const { filteredSampleCount } = useGlobalStorage();
    const { markDownloadClicked } = useExportDialog();

    const trackDialogDefaultFormatSet = (exportFormat: string) => {
        trackEvent('export_dialog_default_format_set', {
            collection_id: collectionId,
            export_format: exportFormat
        });
    };

    const trackFormatSelectOpened = (currentFormat: string) => {
        trackEvent('export_format_select_opened', {
            collection_id: collectionId,
            current_export_format: currentFormat
        });
    };

    const trackFormatSelected = (exportFormat: string) => {
        trackEvent('export_format_selected', {
            collection_id: collectionId,
            export_format: exportFormat
        });
    };

    const handleAnnotationDownloadClick = (exportFormat: string) => {
        markDownloadClicked();
        trackEvent('export_download_clicked', {
            collection_id: collectionId,
            export_format: exportFormat,
            sample_count: get(filteredSampleCount),
            tag_name: null
        });
    };

    const trackExportDownloadClicked = ({
        exportType,
        tagNameToExport,
        sampleCount
    }: TrackExportDownloadClickedParams) => {
        markDownloadClicked();
        trackEvent('export_download_clicked', {
            collection_id: collectionId,
            export_format: exportType,
            sample_count: sampleCount,
            tag_name: tagNameToExport
        });
    };

    const trackExportTriggered = ({
        exportType,
        tagNameToExport,
        sampleCount,
        success
    }: TrackExportTriggeredParams) => {
        trackEvent('export_triggered', {
            collection_id: collectionId,
            export_format: exportType,
            sample_count: sampleCount,
            tag_name: tagNameToExport,
            success
        });
    };

    return {
        trackDialogDefaultFormatSet,
        trackFormatSelectOpened,
        trackFormatSelected,
        handleAnnotationDownloadClick,
        trackExportDownloadClicked,
        trackExportTriggered
    };
}
