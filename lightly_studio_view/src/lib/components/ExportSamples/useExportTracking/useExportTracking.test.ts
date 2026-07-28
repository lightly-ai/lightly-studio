import { writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useExportTracking } from './useExportTracking';

const { mockTrackEvent, mockMarkDownloadClicked } = vi.hoisted(() => ({
    mockTrackEvent: vi.fn(),
    mockMarkDownloadClicked: vi.fn()
}));

vi.mock('$lib/hooks', () => ({
    usePostHog: () => ({ trackEvent: mockTrackEvent }),
    useGlobalStorage: () => ({ filteredSampleCount: writable(42) }),
    useExportDialog: () => ({ markDownloadClicked: mockMarkDownloadClicked })
}));

const COLLECTION_ID = 'col-1';

const defaultExportParams = {
    exportType: 'samples',
    tagNameToExport: 'my-tag',
    sampleCount: 10
};

describe('useExportTracking', () => {
    beforeEach(() => {
        mockTrackEvent.mockClear();
        mockMarkDownloadClicked.mockClear();
    });

    describe('trackDialogDefaultFormatSet', () => {
        it('tracks the event with the given format', () => {
            const { trackDialogDefaultFormatSet } = useExportTracking({
                collectionId: COLLECTION_ID
            });

            trackDialogDefaultFormatSet('samples');

            expect(mockTrackEvent).toHaveBeenCalledWith('export_dialog_default_format_set', {
                collection_id: COLLECTION_ID,
                export_format: 'samples'
            });
        });
    });

    describe('trackFormatSelectOpened', () => {
        it('tracks the event with the current format', () => {
            const { trackFormatSelectOpened } = useExportTracking({ collectionId: COLLECTION_ID });

            trackFormatSelectOpened('captions');

            expect(mockTrackEvent).toHaveBeenCalledWith('export_format_select_opened', {
                collection_id: COLLECTION_ID,
                current_export_format: 'captions'
            });
        });
    });

    describe('trackFormatSelected', () => {
        it('tracks the event with the newly selected format', () => {
            const { trackFormatSelected } = useExportTracking({ collectionId: COLLECTION_ID });

            trackFormatSelected('object_detections_coco');

            expect(mockTrackEvent).toHaveBeenCalledWith('export_format_selected', {
                collection_id: COLLECTION_ID,
                export_format: 'object_detections_coco'
            });
        });
    });

    describe('handleAnnotationDownloadClick', () => {
        it('marks download clicked and tracks the event', () => {
            const { handleAnnotationDownloadClick } = useExportTracking({
                collectionId: COLLECTION_ID
            });

            handleAnnotationDownloadClick('segmentation');

            expect(mockMarkDownloadClicked).toHaveBeenCalledOnce();
            expect(mockTrackEvent).toHaveBeenCalledWith('export_download_clicked', {
                collection_id: COLLECTION_ID,
                export_format: 'segmentation',
                sample_count: 42,
                tag_name: null
            });
        });
    });

    describe('trackExportDownloadClicked', () => {
        it('marks download clicked and tracks export_download_clicked', () => {
            const { trackExportDownloadClicked } = useExportTracking({
                collectionId: COLLECTION_ID
            });

            trackExportDownloadClicked(defaultExportParams);

            expect(mockMarkDownloadClicked).toHaveBeenCalledOnce();
            expect(mockTrackEvent).toHaveBeenCalledWith('export_download_clicked', {
                collection_id: COLLECTION_ID,
                export_format: 'samples',
                sample_count: 10,
                tag_name: 'my-tag'
            });
        });
    });

    describe('trackExportTriggered', () => {
        it('tracks export_triggered with success: true', () => {
            const { trackExportTriggered } = useExportTracking({ collectionId: COLLECTION_ID });

            trackExportTriggered({ ...defaultExportParams, success: true });

            expect(mockTrackEvent).toHaveBeenCalledWith('export_triggered', {
                collection_id: COLLECTION_ID,
                export_format: 'samples',
                sample_count: 10,
                tag_name: 'my-tag',
                success: true
            });
        });

        it('tracks export_triggered with success: false and the error message', () => {
            const { trackExportTriggered } = useExportTracking({ collectionId: COLLECTION_ID });

            trackExportTriggered({
                ...defaultExportParams,
                tagNameToExport: null,
                sampleCount: 5,
                success: false
            });

            expect(mockTrackEvent).toHaveBeenCalledWith('export_triggered', {
                collection_id: COLLECTION_ID,
                export_format: 'samples',
                sample_count: 5,
                tag_name: null,
                success: false
            });
        });
    });
});
