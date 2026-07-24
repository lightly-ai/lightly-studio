import { get } from 'svelte/store';
import type { ImageFilter } from '$lib/api/lightly_studio_local';
import { exportCollection } from '$lib/services/exportCollection';
import type { ExportFilter } from '$lib/services/types';
import { useExportDialog } from '$lib/hooks';
import { useGlobalStorage, usePostHog } from '$lib/hooks';

interface UseExportTrackingParams {
    collectionId: string;
}

interface HandleExportParams {
    exportType: string;
    tagNameToExport: string | null;
    sampleCount: number;
    includeFilter: ExportFilter | undefined;
    excludeFilter: ExportFilter | undefined;
    imageFilter: ImageFilter | null | undefined;
}

interface HandleExportResult {
    errorMessage: string | undefined;
}

export function useExportTracking({ collectionId }: UseExportTrackingParams) {
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

    const handleExport = async ({
        exportType,
        tagNameToExport,
        sampleCount,
        includeFilter,
        excludeFilter,
        imageFilter
    }: HandleExportParams): Promise<HandleExportResult> => {
        markDownloadClicked();
        trackEvent('export_download_clicked', {
            collection_id: collectionId,
            export_format: exportType,
            sample_count: sampleCount,
            tag_name: tagNameToExport
        });

        const response = await exportCollection({
            collection_id: collectionId,
            includeFilter,
            excludeFilter,
            collectionFilter: imageFilter
        });

        trackEvent('export_triggered', {
            collection_id: collectionId,
            export_format: exportType,
            sample_count: sampleCount,
            tag_name: tagNameToExport,
            success: !response.error,
            error_message: response.error ?? null
        });

        return {
            errorMessage: response.error ? `Export failed: ${response.error}` : undefined
        };
    };

    return {
        trackDialogDefaultFormatSet,
        trackFormatSelectOpened,
        trackFormatSelected,
        handleAnnotationDownloadClick,
        handleExport
    };
}
