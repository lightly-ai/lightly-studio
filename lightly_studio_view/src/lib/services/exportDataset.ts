import type { ExportFilter, LoadResult } from '$lib/services/types';
import { triggerDownloadBlob } from '$lib/utils';
import { client } from './dataset';

type ExportDatasetResult = LoadResult<Blob | undefined>;
type ExportDatasetParams = {
    dataset_id: string;
    filename?: string;
    includeFilter?: ExportFilter;
    excludeFilter?: ExportFilter;
};

// TODO: properly abstract each endpoint and use the types of client to make the request
export const exportDataset = async ({
    dataset_id,
    filename = '',
    includeFilter,
    excludeFilter
}: ExportDatasetParams): Promise<ExportDatasetResult> => {
    const result: ExportDatasetResult = { data: undefined, error: undefined };
    try {
        const response = await client.POST('/api/datasets/{dataset_id}/export', {
            params: {
                path: {
                    dataset_id: dataset_id
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
        result.error = 'Error exporting dataset: ' + String(e);
    }

    return result;
};
