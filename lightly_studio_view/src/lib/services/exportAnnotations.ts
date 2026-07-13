import { client } from '$lib/api/lightly_studio_local/client.gen';
import type { ExportFormat } from '$lib/api/lightly_studio_local';
import { triggerDownloadUrl } from '$lib/utils';

type ExportResult = { error?: string };

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
        const baseUrl = (client.getConfig().baseUrl ?? '').replace(/\/$/, '');
        const url = new URL(
            `${baseUrl}/api/collections/${encodeURIComponent(collection_id)}/export/annotations`
        );
        if (annotation_collection_id) {
            url.searchParams.set('annotation_collection_id', annotation_collection_id);
        }
        if (export_format) {
            url.searchParams.set('export_format', export_format);
        }
        triggerDownloadUrl(url.toString());
        return {};
    } catch (e) {
        return { error: 'Export failed: ' + String(e) };
    }
};

export const exportCaptions = async (collection_id: string): Promise<ExportResult> => {
    try {
        const baseUrl = (client.getConfig().baseUrl ?? '').replace(/\/$/, '');
        const url = new URL(
            `${baseUrl}/api/collections/${encodeURIComponent(collection_id)}/export/captions`
        );
        triggerDownloadUrl(url.toString());
        return {};
    } catch (e) {
        return { error: 'Export failed: ' + String(e) };
    }
};
