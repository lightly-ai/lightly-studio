import type { ExportFilter, LoadResult } from '$lib/services/types';
import { triggerDownloadBlob } from '$lib/utils';
import { client } from './collection';

type ExportCollectionResult = LoadResult<Blob | undefined>;
type ExportCollectionParams = {
    collection_id: string;
    filename?: string;
    includeFilter?: ExportFilter;
    excludeFilter?: ExportFilter;
};

// TODO: properly abstract each endpoint and use the types of client to make the request
export const exportCollection = async ({
    collection_id,
    filename = '',
    includeFilter,
    excludeFilter
}: ExportCollectionParams): Promise<ExportCollectionResult> => {
    const result: ExportCollectionResult = { data: undefined, error: undefined };
    try {
        const response = await client.POST('/api/collections/{collection_id}/export', {
            params: {
                path: {
                    collection_id: collection_id
                }
            },
            body: {
                include: includeFilter,
                exclude: excludeFilter
            },
            headers: {
                'Access-Control-Expose-Headers': 'Content-Disposition'
            },
            parseAs: 'blob'
        });
        if (response.error) {
            throw new Error(JSON.stringify(response.error, null, 2));
        }

        if (!response.data) {
            throw new Error('No data');
        }
        result.data = response.data;

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
