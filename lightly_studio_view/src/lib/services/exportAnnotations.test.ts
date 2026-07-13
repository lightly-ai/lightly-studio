import { describe, it, expect, vi, beforeEach } from 'vitest';
import { exportAnnotations, exportCaptions } from './exportAnnotations';

vi.mock('$lib/api/lightly_studio_local/sdk.gen', () => ({
    exportCollectionAnnotations: vi.fn(),
    exportCollectionCaptions: vi.fn()
}));

vi.mock('$lib/utils', () => ({
    triggerDownloadBlob: vi.fn()
}));

const { exportCollectionAnnotations, exportCollectionCaptions } =
    await import('$lib/api/lightly_studio_local/sdk.gen');
const { triggerDownloadBlob } = await import('$lib/utils');

describe('exportAnnotations', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('calls exportCollectionAnnotations with correct params and triggers download', async () => {
        const mockBlob = new Blob(['data']);
        const mockResponse = new Response();
        vi.spyOn(mockResponse.headers, 'get').mockReturnValue(
            'attachment; filename=annotations.zip'
        );

        vi.mocked(exportCollectionAnnotations).mockResolvedValue({
            data: mockBlob,
            error: undefined,
            request: {} as Request,
            response: mockResponse
        });

        const result = await exportAnnotations('collection-123', {
            annotation_collection_id: 'ac-1'
        });

        expect(exportCollectionAnnotations).toHaveBeenCalledWith({
            path: { collection_id: 'collection-123' },
            body: { annotation_collection_id: 'ac-1' },
            parseAs: 'blob'
        });
        expect(triggerDownloadBlob).toHaveBeenCalledWith('annotations.zip', mockBlob);
        expect(result).toEqual({});
    });

    it('falls back to "export" filename when content-disposition header is absent', async () => {
        const mockBlob = new Blob(['data']);
        const mockResponse = new Response();
        vi.spyOn(mockResponse.headers, 'get').mockReturnValue(null);

        vi.mocked(exportCollectionAnnotations).mockResolvedValue({
            data: mockBlob,
            error: undefined,
            request: {} as Request,
            response: mockResponse
        });

        await exportAnnotations('collection-123', {});

        expect(triggerDownloadBlob).toHaveBeenCalledWith('export', mockBlob);
    });

    it('returns error when response.error is set', async () => {
        vi.mocked(exportCollectionAnnotations).mockResolvedValue({
            data: undefined,
            error: { detail: [] },
            request: {} as Request,
            response: {} as Response
        });

        const result = await exportAnnotations('collection-123', {});

        expect(result.error).toContain('Export failed:');
        expect(triggerDownloadBlob).not.toHaveBeenCalled();
    });

    it('returns error when response.data is missing', async () => {
        const mockResponse = new Response();
        vi.spyOn(mockResponse.headers, 'get').mockReturnValue(null);

        vi.mocked(exportCollectionAnnotations).mockResolvedValue({
            data: undefined,
            error: undefined,
            request: {} as Request,
            response: mockResponse
        });

        const result = await exportAnnotations('collection-123', {});

        expect(result.error).toContain('Export failed:');
        expect(triggerDownloadBlob).not.toHaveBeenCalled();
    });

    it('returns error when API call throws', async () => {
        vi.mocked(exportCollectionAnnotations).mockRejectedValue(new Error('Network error'));

        const result = await exportAnnotations('collection-123', {});

        expect(result.error).toBe('Export failed: Error: Network error');
        expect(triggerDownloadBlob).not.toHaveBeenCalled();
    });
});

describe('exportCaptions', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('calls exportCollectionCaptions with correct params and triggers download', async () => {
        const mockBlob = new Blob(['data']);
        const mockResponse = new Response();
        vi.spyOn(mockResponse.headers, 'get').mockReturnValue('attachment; filename=captions.json');

        vi.mocked(exportCollectionCaptions).mockResolvedValue({
            data: mockBlob,
            error: undefined,
            request: {} as Request,
            response: mockResponse
        });

        const result = await exportCaptions('collection-456', {});

        expect(exportCollectionCaptions).toHaveBeenCalledWith({
            path: { collection_id: 'collection-456' },
            body: {},
            parseAs: 'blob'
        });
        expect(triggerDownloadBlob).toHaveBeenCalledWith('captions.json', mockBlob);
        expect(result).toEqual({});
    });

    it('falls back to "export" filename when content-disposition header is absent', async () => {
        const mockBlob = new Blob(['data']);
        const mockResponse = new Response();
        vi.spyOn(mockResponse.headers, 'get').mockReturnValue(null);

        vi.mocked(exportCollectionCaptions).mockResolvedValue({
            data: mockBlob,
            error: undefined,
            request: {} as Request,
            response: mockResponse
        });

        await exportCaptions('collection-456', {});

        expect(triggerDownloadBlob).toHaveBeenCalledWith('export', mockBlob);
    });

    it('returns error when response.error is set', async () => {
        vi.mocked(exportCollectionCaptions).mockResolvedValue({
            data: undefined,
            error: { detail: [] },
            request: {} as Request,
            response: {} as Response
        });

        const result = await exportCaptions('collection-456', {});

        expect(result.error).toContain('Export failed:');
        expect(triggerDownloadBlob).not.toHaveBeenCalled();
    });

    it('returns error when response.data is missing', async () => {
        const mockResponse = new Response();
        vi.spyOn(mockResponse.headers, 'get').mockReturnValue(null);

        vi.mocked(exportCollectionCaptions).mockResolvedValue({
            data: undefined,
            error: undefined,
            request: {} as Request,
            response: mockResponse
        });

        const result = await exportCaptions('collection-456', {});

        expect(result.error).toContain('Export failed:');
        expect(triggerDownloadBlob).not.toHaveBeenCalled();
    });

    it('returns error when API call throws', async () => {
        vi.mocked(exportCollectionCaptions).mockRejectedValue(new Error('Network error'));

        const result = await exportCaptions('collection-456', {});

        expect(result.error).toBe('Export failed: Error: Network error');
        expect(triggerDownloadBlob).not.toHaveBeenCalled();
    });
});
