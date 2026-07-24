import { get, writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useExportDialog } from './useExportDialog';

const mockTrackEvent = vi.fn();

vi.mock('$lib/hooks/usePostHog', () => ({
    usePostHog: () => ({ trackEvent: mockTrackEvent })
}));

vi.mock('$lib/hooks/useGlobalStorage', () => ({
    useGlobalStorage: () => ({ filteredSampleCount: writable(0) })
}));

describe('useExportDialog', () => {
    beforeEach(() => {
        mockTrackEvent.mockClear();

        // Reset shared store state between tests by closing any open dialog
        const { closeExportDialog, isExportDialogOpen } = useExportDialog();
        if (get(isExportDialogOpen)) {
            closeExportDialog({ collectionId: 'reset', exportFormat: 'samples' });
        }
        mockTrackEvent.mockClear();
    });

    describe('openExportDialog', () => {
        it('sets isExportDialogOpen to true', () => {
            const { isExportDialogOpen, openExportDialog } = useExportDialog();

            openExportDialog({ collectionId: 'col-1' });

            expect(get(isExportDialogOpen)).toBe(true);
        });

        it('tracks export_dialog_opened', () => {
            const { openExportDialog } = useExportDialog();

            openExportDialog({ collectionId: 'col-1' });

            expect(mockTrackEvent).toHaveBeenCalledWith('export_dialog_opened', {
                collection_id: 'col-1',
                filtered_sample_count: expect.anything()
            });
        });

        it('does nothing when dialog is already open', () => {
            const { openExportDialog } = useExportDialog();

            openExportDialog({ collectionId: 'col-1' });
            openExportDialog({ collectionId: 'col-1' });

            expect(mockTrackEvent).toHaveBeenCalledTimes(1);
        });
    });

    describe('closeExportDialog', () => {
        it('sets isExportDialogOpen to false', () => {
            const { isExportDialogOpen, openExportDialog, closeExportDialog } = useExportDialog();
            openExportDialog({ collectionId: 'col-1' });

            closeExportDialog({ collectionId: 'col-1', exportFormat: 'samples' });

            expect(get(isExportDialogOpen)).toBe(false);
        });

        it('tracks export_dialog_dismissed when no download occurred', () => {
            const { openExportDialog, closeExportDialog } = useExportDialog();
            openExportDialog({ collectionId: 'col-1' });
            mockTrackEvent.mockClear();

            closeExportDialog({ collectionId: 'col-1', exportFormat: 'samples' });

            expect(mockTrackEvent).toHaveBeenCalledWith('export_dialog_dismissed', {
                collection_id: 'col-1',
                export_format: 'samples'
            });
        });

        it('does not track export_dialog_dismissed when a download was clicked', () => {
            const { openExportDialog, closeExportDialog, markDownloadClicked } = useExportDialog();
            openExportDialog({ collectionId: 'col-1' });
            markDownloadClicked();
            mockTrackEvent.mockClear();

            closeExportDialog({ collectionId: 'col-1', exportFormat: 'samples' });

            expect(mockTrackEvent).not.toHaveBeenCalledWith(
                'export_dialog_dismissed',
                expect.anything()
            );
        });

        it('does nothing when dialog is already closed', () => {
            const { closeExportDialog } = useExportDialog();

            closeExportDialog({ collectionId: 'col-1', exportFormat: 'samples' });

            expect(mockTrackEvent).not.toHaveBeenCalled();
        });
    });

    describe('markDownloadClicked', () => {
        it('resets between sessions so closing without download after a new open tracks dismissed', () => {
            const { openExportDialog, closeExportDialog, markDownloadClicked } = useExportDialog();

            // First session: download clicked, close → no dismissed event
            openExportDialog({ collectionId: 'col-1' });
            markDownloadClicked();
            closeExportDialog({ collectionId: 'col-1', exportFormat: 'samples' });
            mockTrackEvent.mockClear();

            // Second session: no download, close → dismissed event fires
            openExportDialog({ collectionId: 'col-1' });
            mockTrackEvent.mockClear();
            closeExportDialog({ collectionId: 'col-1', exportFormat: 'samples' });

            expect(mockTrackEvent).toHaveBeenCalledWith('export_dialog_dismissed', {
                collection_id: 'col-1',
                export_format: 'samples'
            });
        });
    });
});
