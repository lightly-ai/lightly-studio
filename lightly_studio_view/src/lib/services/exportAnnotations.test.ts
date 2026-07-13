import { exportAnnotations, exportCaptions } from './exportAnnotations';
import * as clientModule from '$lib/api/lightly_studio_local/client.gen';
import { ExportFormat } from '$lib/api/lightly_studio_local';
import { vi } from 'vitest';

vi.mock('$lib/utils', () => ({
    triggerDownloadUrl: vi.fn()
}));

import { triggerDownloadUrl } from '$lib/utils';

const BASE_URL = 'http://localhost:8001/';

describe('exportAnnotations', () => {
    beforeEach(() => {
        vi.mocked(clientModule.client).getConfig = vi.fn().mockReturnValue({ baseUrl: BASE_URL });
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.mocked(triggerDownloadUrl).mockClear();
    });

    it('constructs URL with collection_id and annotation_collection_id, triggers download', async () => {
        const result = await exportAnnotations({
            collection_id: 'col1',
            annotation_collection_id: 'ann1'
        });

        expect(result).toEqual({});
        expect(triggerDownloadUrl).toHaveBeenCalledWith(
            'http://localhost:8001/api/collections/col1/export/annotations?annotation_collection_id=ann1'
        );
    });

    it('includes export_format in URL query when provided', async () => {
        await exportAnnotations({
            collection_id: 'col1',
            annotation_collection_id: 'ann1',
            export_format: ExportFormat.OBJECT_DETECTION_YOLO
        });

        expect(triggerDownloadUrl).toHaveBeenCalledWith(
            `http://localhost:8001/api/collections/col1/export/annotations?annotation_collection_id=ann1&export_format=${ExportFormat.OBJECT_DETECTION_YOLO}`
        );
    });

    it('omits annotation_collection_id from URL when null', async () => {
        await exportAnnotations({
            collection_id: 'col1',
            annotation_collection_id: null
        });

        expect(triggerDownloadUrl).toHaveBeenCalledWith(
            'http://localhost:8001/api/collections/col1/export/annotations'
        );
    });

    it('strips trailing slash from baseUrl before constructing URL', async () => {
        vi.mocked(clientModule.client).getConfig = vi
            .fn()
            .mockReturnValue({ baseUrl: 'http://localhost:8001/' });

        await exportAnnotations({ collection_id: 'col1', annotation_collection_id: null });

        const url = vi.mocked(triggerDownloadUrl).mock.calls[0][0];
        expect(url).not.toContain('//api');
    });

    it('returns error when URL construction throws', async () => {
        vi.mocked(clientModule.client).getConfig = vi.fn().mockImplementation(() => {
            throw new Error('config error');
        });

        const result = await exportAnnotations({
            collection_id: 'col1',
            annotation_collection_id: null
        });

        expect(result.error).toBeDefined();
        expect(triggerDownloadUrl).not.toHaveBeenCalled();
    });
});

describe('exportCaptions', () => {
    beforeEach(() => {
        vi.mocked(clientModule.client).getConfig = vi.fn().mockReturnValue({ baseUrl: BASE_URL });
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.mocked(triggerDownloadUrl).mockClear();
    });

    it('constructs URL with collection_id and triggers download', async () => {
        const result = await exportCaptions('col1');

        expect(result).toEqual({});
        expect(triggerDownloadUrl).toHaveBeenCalledWith(
            'http://localhost:8001/api/collections/col1/export/captions'
        );
    });

    it('returns error when URL construction throws', async () => {
        vi.mocked(clientModule.client).getConfig = vi.fn().mockImplementation(() => {
            throw new Error('config error');
        });

        const result = await exportCaptions('col1');

        expect(result.error).toBeDefined();
        expect(triggerDownloadUrl).not.toHaveBeenCalled();
    });
});
