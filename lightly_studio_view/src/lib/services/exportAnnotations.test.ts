import { exportAnnotations, exportCaptions } from './exportAnnotations';
import * as sdk from '$lib/api/lightly_studio_local/sdk.gen';
import { ExportFormat } from '$lib/api/lightly_studio_local';
import { vi } from 'vitest';

vi.mock('$lib/utils', () => ({
    triggerDownloadBlob: vi.fn()
}));

import { triggerDownloadBlob } from '$lib/utils';

type ExportCollectionAnnotationsReturn = Awaited<
    ReturnType<typeof sdk.exportCollectionAnnotations>
>;
type ExportCollectionCaptionsReturn = Awaited<ReturnType<typeof sdk.exportCollectionCaptions>>;

const makeResponse = (filename?: string) =>
    new Response(null, {
        headers: filename ? { 'content-disposition': `attachment; filename=${filename}` } : {}
    });

describe('exportAnnotations', () => {
    afterEach(() => {
        vi.restoreAllMocks();
        vi.mocked(triggerDownloadBlob).mockClear();
    });

    it('calls SDK with correct path and query, triggers download with filename from header', async () => {
        const blob = new Blob(['data']);
        const mockedFn = vi.spyOn(sdk, 'exportCollectionAnnotations').mockResolvedValue({
            data: blob,
            error: undefined,
            response: makeResponse('annotations.zip')
        } as unknown as ExportCollectionAnnotationsReturn);

        const result = await exportAnnotations({
            collection_id: 'col1',
            annotation_collection_id: 'ann1'
        });

        expect(result).toEqual({});
        expect(mockedFn).toHaveBeenCalledWith({
            path: { collection_id: 'col1' },
            query: { annotation_collection_id: 'ann1', export_format: undefined },
            parseAs: 'blob'
        });
        expect(triggerDownloadBlob).toHaveBeenCalledWith('annotations.zip', blob);
    });

    it('passes export_format to SDK query when provided', async () => {
        const blob = new Blob(['data']);
        const mockedFn = vi.spyOn(sdk, 'exportCollectionAnnotations').mockResolvedValue({
            data: blob,
            error: undefined,
            response: makeResponse('export.zip')
        } as unknown as ExportCollectionAnnotationsReturn);

        await exportAnnotations({
            collection_id: 'col1',
            annotation_collection_id: 'ann1',
            export_format: ExportFormat.OBJECT_DETECTION_YOLO
        });

        expect(mockedFn).toHaveBeenCalledWith({
            path: { collection_id: 'col1' },
            query: {
                annotation_collection_id: 'ann1',
                export_format: ExportFormat.OBJECT_DETECTION_YOLO
            },
            parseAs: 'blob'
        });
    });

    it('returns error and does not trigger download when response.error is set', async () => {
        vi.spyOn(sdk, 'exportCollectionAnnotations').mockResolvedValue({
            data: undefined,
            error: 'Not Found',
            response: makeResponse()
        } as unknown as ExportCollectionAnnotationsReturn);

        const result = await exportAnnotations({
            collection_id: 'col1',
            annotation_collection_id: null
        });

        expect(result.error).toBeDefined();
        expect(triggerDownloadBlob).not.toHaveBeenCalled();
    });

    it('returns error and does not trigger download when response.data is null', async () => {
        vi.spyOn(sdk, 'exportCollectionAnnotations').mockResolvedValue({
            data: null,
            error: undefined,
            response: makeResponse()
        } as unknown as ExportCollectionAnnotationsReturn);

        const result = await exportAnnotations({
            collection_id: 'col1',
            annotation_collection_id: null
        });

        expect(result.error).toBeDefined();
        expect(triggerDownloadBlob).not.toHaveBeenCalled();
    });

    it('returns error and does not trigger download when SDK call rejects', async () => {
        vi.spyOn(sdk, 'exportCollectionAnnotations').mockRejectedValue(new Error('network error'));

        const result = await exportAnnotations({
            collection_id: 'col1',
            annotation_collection_id: null
        });

        expect(result.error).toBeDefined();
        expect(triggerDownloadBlob).not.toHaveBeenCalled();
    });

    it('uses fallback filename "export" when Content-Disposition header is absent', async () => {
        const blob = new Blob(['data']);
        vi.spyOn(sdk, 'exportCollectionAnnotations').mockResolvedValue({
            data: blob,
            error: undefined,
            response: makeResponse()
        } as unknown as ExportCollectionAnnotationsReturn);

        await exportAnnotations({
            collection_id: 'col1',
            annotation_collection_id: null
        });

        expect(triggerDownloadBlob).toHaveBeenCalledWith('export', blob);
    });
});

describe('exportCaptions', () => {
    afterEach(() => {
        vi.restoreAllMocks();
        vi.mocked(triggerDownloadBlob).mockClear();
    });

    it('calls SDK with correct path and triggers download with filename from header', async () => {
        const blob = new Blob(['captions']);
        const mockedFn = vi.spyOn(sdk, 'exportCollectionCaptions').mockResolvedValue({
            data: blob,
            error: undefined,
            response: makeResponse('captions.json')
        } as unknown as ExportCollectionCaptionsReturn);

        const result = await exportCaptions('col1');

        expect(result).toEqual({});
        expect(mockedFn).toHaveBeenCalledWith({
            path: { collection_id: 'col1' },
            parseAs: 'blob'
        });
        expect(triggerDownloadBlob).toHaveBeenCalledWith('captions.json', blob);
    });

    it('returns error and does not trigger download when response.error is set', async () => {
        vi.spyOn(sdk, 'exportCollectionCaptions').mockResolvedValue({
            data: undefined,
            error: 'Forbidden',
            response: makeResponse()
        } as unknown as ExportCollectionCaptionsReturn);

        const result = await exportCaptions('col1');

        expect(result.error).toBeDefined();
        expect(triggerDownloadBlob).not.toHaveBeenCalled();
    });

    it('returns error and does not trigger download when response.data is null', async () => {
        vi.spyOn(sdk, 'exportCollectionCaptions').mockResolvedValue({
            data: null,
            error: undefined,
            response: makeResponse()
        } as unknown as ExportCollectionCaptionsReturn);

        const result = await exportCaptions('col1');

        expect(result.error).toBeDefined();
        expect(triggerDownloadBlob).not.toHaveBeenCalled();
    });

    it('returns error and does not trigger download when SDK call rejects', async () => {
        vi.spyOn(sdk, 'exportCollectionCaptions').mockRejectedValue(new Error('timeout'));

        const result = await exportCaptions('col1');

        expect(result.error).toBeDefined();
        expect(triggerDownloadBlob).not.toHaveBeenCalled();
    });
});
