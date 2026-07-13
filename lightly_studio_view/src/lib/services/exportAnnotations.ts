import {
    exportCollectionAnnotations,
    exportCollectionCaptions,
    type ExportFormat
} from '$lib/api/lightly_studio_local';
import { triggerDownloadBlob } from '$lib/utils';

type ExportResult = { error?: string };

const getFilename = (response: Response): string =>
    response.headers.get('content-disposition')?.match(/filename="?([^";]+)"?/)?.[1] ?? 'export';

export const exportAnnotations = async ({
    collection_id,
    annotation_collection_id,
    export_format
}: {
    collection_id: string;
    annotation_collection_id: string | null;
    export_format?: ExportFormat;
}): Promise<ExportResult> => {
    try {
        const response = await exportCollectionAnnotations({
            path: { collection_id },
            query: { annotation_collection_id, export_format },
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

export const exportCaptions = async (collection_id: string): Promise<ExportResult> => {
    try {
        const response = await exportCollectionCaptions({
            path: { collection_id },
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
