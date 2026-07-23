import { writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useExportTracking } from './useExportTracking';

const mockTrackEvent = vi.fn();
const mockMarkDownloadClicked = vi.fn();
const mockExportCollection = vi.fn();

vi.mock('$lib/hooks/usePostHog', () => ({
    usePostHog: () => ({ trackEvent: mockTrackEvent })
}));

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({ filteredSampleCount: writable(42) })
}));

vi.mock('$lib/hooks', () => ({
    useExportDialog: () => ({ markDownloadClicked: mockMarkDownloadClicked })
}));

vi.mock('$lib/services/exportCollection', () => ({
    exportCollection: (...args: unknown[]) => mockExportCollection(...args)
}));

const COLLECTION_ID = 'col-1';

describe('useExportTracking', () => {
    beforeEach(() => {
        mockTrackEvent.mockClear();
        mockMarkDownloadClicked.mockClear();
        mockExportCollection.mockClear();
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

    describe('handleExport', () => {
        it('marks download clicked and tracks export_download_clicked before the request', async () => {
            mockExportCollection.mockResolvedValue({ error: undefined });
            const { handleExport } = useExportTracking({ collectionId: COLLECTION_ID });

            await handleExport({
                exportType: 'samples',
                tagNameToExport: 'my-tag',
                sampleCount: 10,
                includeFilter: undefined,
                excludeFilter: undefined,
                imageFilter: null
            });

            expect(mockMarkDownloadClicked).toHaveBeenCalledOnce();
            expect(mockTrackEvent).toHaveBeenCalledWith('export_download_clicked', {
                collection_id: COLLECTION_ID,
                export_format: 'samples',
                sample_count: 10,
                tag_name: 'my-tag'
            });
        });

        it('tracks export_triggered with success on a successful response', async () => {
            mockExportCollection.mockResolvedValue({ error: undefined });
            const { handleExport } = useExportTracking({ collectionId: COLLECTION_ID });

            await handleExport({
                exportType: 'samples',
                tagNameToExport: 'my-tag',
                sampleCount: 10,
                includeFilter: undefined,
                excludeFilter: undefined,
                imageFilter: null
            });

            expect(mockTrackEvent).toHaveBeenCalledWith('export_triggered', {
                collection_id: COLLECTION_ID,
                export_format: 'samples',
                sample_count: 10,
                tag_name: 'my-tag',
                success: true,
                error_message: null
            });
        });

        it('returns undefined errorMessage on success', async () => {
            mockExportCollection.mockResolvedValue({ error: undefined });
            const { handleExport } = useExportTracking({ collectionId: COLLECTION_ID });

            const result = await handleExport({
                exportType: 'samples',
                tagNameToExport: null,
                sampleCount: 5,
                includeFilter: undefined,
                excludeFilter: undefined,
                imageFilter: null
            });

            expect(result.errorMessage).toBeUndefined();
        });

        it('tracks export_triggered with failure and returns an errorMessage on error', async () => {
            mockExportCollection.mockResolvedValue({ error: 'network timeout' });
            const { handleExport } = useExportTracking({ collectionId: COLLECTION_ID });

            const result = await handleExport({
                exportType: 'samples',
                tagNameToExport: null,
                sampleCount: 5,
                includeFilter: undefined,
                excludeFilter: undefined,
                imageFilter: null
            });

            expect(mockTrackEvent).toHaveBeenCalledWith('export_triggered', {
                collection_id: COLLECTION_ID,
                export_format: 'samples',
                sample_count: 5,
                tag_name: null,
                success: false,
                error_message: 'network timeout'
            });
            expect(result.errorMessage).toBe('Export failed: network timeout');
        });

        it('passes filters and imageFilter through to exportCollection', async () => {
            mockExportCollection.mockResolvedValue({ error: undefined });
            const { handleExport } = useExportTracking({ collectionId: COLLECTION_ID });
            const includeFilter = { tag_ids: ['tag-1'] };
            const imageFilter = { brightness: { min: 0.5 } } as never;

            await handleExport({
                exportType: 'samples',
                tagNameToExport: null,
                sampleCount: 3,
                includeFilter,
                excludeFilter: undefined,
                imageFilter
            });

            expect(mockExportCollection).toHaveBeenCalledWith({
                collection_id: COLLECTION_ID,
                includeFilter,
                excludeFilter: undefined,
                collectionFilter: imageFilter
            });
        });

        it('uses snapshotted values for tracking even if called with different args later', async () => {
            mockExportCollection.mockResolvedValue({ error: undefined });
            const { handleExport } = useExportTracking({ collectionId: COLLECTION_ID });

            await handleExport({
                exportType: 'captions',
                tagNameToExport: 'original-tag',
                sampleCount: 7,
                includeFilter: undefined,
                excludeFilter: undefined,
                imageFilter: null
            });

            const downloadCall = mockTrackEvent.mock.calls.find(
                ([event]) => event === 'export_download_clicked'
            );
            const triggeredCall = mockTrackEvent.mock.calls.find(
                ([event]) => event === 'export_triggered'
            );

            expect(downloadCall?.[1]).toMatchObject({
                export_format: 'captions',
                tag_name: 'original-tag',
                sample_count: 7
            });
            expect(triggeredCall?.[1]).toMatchObject({
                export_format: 'captions',
                tag_name: 'original-tag',
                sample_count: 7
            });
        });
    });
});
