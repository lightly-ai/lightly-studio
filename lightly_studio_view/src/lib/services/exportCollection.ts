import { exportCollectionToAbsolutePaths, type ImageFilter } from '$lib/api/lightly_studio_local';
import type { ExportFilter, LoadResult } from '$lib/services/types';
import { triggerDownloadBlob } from '$lib/utils';

type ExportCollectionResult = LoadResult<Blob | undefined>;
type ExportCollectionParams = {
    collection_id: string;
    filename?: string;
    includeFilter?: ExportFilter;
    excludeFilter?: ExportFilter;
    collectionFilter?: ImageFilter | null;
};

export const exportCollection = async ({
    collection_id,
    filename = '',
    includeFilter,
    excludeFilter,
    collectionFilter
}: ExportCollectionParams): Promise<ExportCollectionResult> => {
    const result: ExportCollectionResult = { data: undefined, error: undefined };
    try {
        const response = await exportCollectionToAbsolutePaths({
            path: { collection_id },
            body: {
                include: includeFilter,
                exclude: excludeFilter,
                collection_filter: collectionFilter
            },
            headers: {
                'Access-Control-Expose-Headers': 'Content-Disposition'
            },
            parseAs: 'text'
        });
        if (response.error) {
            throw new Error(JSON.stringify(response.error, null, 2));
        }

        if (!response.data || typeof response.data !== 'string') {
            throw new Error('No data');
        }
        result.data = new Blob([response.data], { type: 'text/plain' });

        // trigger download as a certain filename
        filename =
            filename ||
            response.response.headers.get('content-disposition')?.split('filename=')[1] ||
            `export_${new Date().toISOString()}.txt`;

        triggerDownloadBlob(filename, result.data);
    } catch (e) {
        result.error = 'Error exporting collection: ' + String(e);
    }

    return result;
};
