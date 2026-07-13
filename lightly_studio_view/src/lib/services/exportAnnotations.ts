import {
    exportCollectionAnnotations,
    exportCollectionCaptions
} from '$lib/api/lightly_studio_local';
import type { ExportAnnotationsBody, ExportCaptionsBody } from '$lib/api/lightly_studio_local';
import { triggerDownloadBlob } from '$lib/utils';

type ExportResult = { error?: string };

const getFilename = (response: Response): string =>
    response.headers.get('content-disposition')?.split('filename=')[1] ?? 'export';

export const exportAnnotations = async (
    collection_id: string,
    body: ExportAnnotationsBody
): Promise<ExportResult> => {
    try {
        const response = await exportCollectionAnnotations({
            path: { collection_id },
            body,
            parseAs: 'blob'
        });
        if (response.error) throw new Error(JSON.stringify(response.error));
        if (!response.data) throw new Error('No data');
        triggerDownloadBlob(getFilename(response.response), response.data as Blob);
        return {};
    } catch (e) {
        return { error: 'Export failed: ' + String(e) };
    }
};

export const exportCaptions = async (
    collection_id: string,
    body: ExportCaptionsBody
): Promise<ExportResult> => {
    try {
        const response = await exportCollectionCaptions({
            path: { collection_id },
            body,
            parseAs: 'blob'
        });
        if (response.error) throw new Error(JSON.stringify(response.error));
        if (!response.data) throw new Error('No data');
        triggerDownloadBlob(getFilename(response.response), response.data as Blob);
        return {};
    } catch (e) {
        return { error: 'Export failed: ' + String(e) };
    }
};
