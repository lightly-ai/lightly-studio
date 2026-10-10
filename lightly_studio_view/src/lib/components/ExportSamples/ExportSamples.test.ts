import { fireEvent, render, screen, waitFor } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ExportSamples from './ExportSamples.svelte';

const pageMock = vi.hoisted(() => ({
    params: { collection_id: 'test-collection' },
    data: { collection: { sample_type: 'image' } }
}));
vi.mock('$app/state', () => ({ page: pageMock }));

const mocks = vi.hoisted(() => ({
    exportCollectionPrepare: vi.fn(),
    triggerDownload: vi.fn()
}));

vi.mock('$lib/api/lightly_studio_local', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/api/lightly_studio_local')>();
    return {
        ...actual,
        exportCollectionPrepare: mocks.exportCollectionPrepare
    };
});

vi.mock('./useExportDownload', async (importOriginal) => {
    const actual = await importOriginal<typeof import('./useExportDownload')>();
    return {
        ...actual,
        triggerDownload: mocks.triggerDownload
    };
});

const isExportDialogOpenStore = writable(true);

vi.mock('$lib/hooks', () => ({
    useExportDialog: () => ({
        isExportDialogOpen: isExportDialogOpenStore,
        openExportDialog: vi.fn(),
        closeExportDialog: vi.fn()
    }),
    useGlobalStorage: () => ({
        filteredSampleCount: writable(100)
    }),
    useAnnotationCollections: () => ({ data: [] }),
    useImageFilters: () => ({ imageFilter: writable(null) }),
    useVideoFilters: () => ({ videoFilter: writable(null) })
}));

vi.mock('./useExportTracking/useExportTracking', () => ({
    useExportTracking: () => ({
        handleAnnotationDownloadClick: vi.fn(),
        trackExportTriggered: vi.fn(),
        trackDialogDefaultFormatSet: vi.fn(),
        trackFormatSelectOpened: vi.fn(),
        trackFormatSelected: vi.fn(),
        trackExportDownloadClicked: vi.fn()
    })
}));

vi.mock('$env/static/public', () => ({
    PUBLIC_LIGHTLY_STUDIO_API_URL: 'http://localhost:8000/'
}));

describe('ExportSamples', () => {
    beforeEach(() => {
        mocks.exportCollectionPrepare.mockReset();
        mocks.triggerDownload.mockReset();
        isExportDialogOpenStore.set(true);
    });

    it('the export-type select is enabled when no export is in progress', () => {
        render(ExportSamples);
        expect(screen.getByTestId('export-type-select')).not.toBeDisabled();
    });

    it('disables the export-type select while an export is pending and re-enables it on completion', async () => {
        let resolveExport!: () => void;
        mocks.exportCollectionPrepare.mockReturnValue(
            new Promise<{ data: { export_key: string } }>((resolve) => {
                resolveExport = () => resolve({ data: { export_key: 'key123' } });
            })
        );

        render(ExportSamples);

        await fireEvent.click(screen.getByTestId('submit-button-samples'));
        await waitFor(() => expect(screen.getByTestId('export-type-select')).toBeDisabled());

        resolveExport();
        await waitFor(() => expect(screen.getByTestId('export-type-select')).not.toBeDisabled());
    });
});
