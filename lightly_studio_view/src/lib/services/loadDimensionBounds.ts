import { client } from './dataset';
import type { LoadResult } from './types';

export type DimensionBounds = {
    min_width: number;
    max_width: number;
    min_height: number;
    max_height: number;
};

type LoadDimensionBoundsParams = {
    dataset_id: string;
    annotation_label_ids?: string[];
};

export const loadDimensionBounds = async ({
    dataset_id,
    annotation_label_ids
}: LoadDimensionBoundsParams): Promise<LoadResult<DimensionBounds | undefined>> => {
    const result: LoadResult<DimensionBounds | undefined> = {
        data: undefined,
        error: undefined
    };

    try {
        const response = await client.GET('/api/datasets/{dataset_id}/images/dimensions', {
            params: {
                path: {
                    dataset_id
                },
                query: {
                    annotation_label_ids
                }
            }
        });

        if (response.error) {
            throw new Error(JSON.stringify(response.error, null, 2));
        }

        if (!response.data) {
            throw new Error('No dimension bounds data');
        }

        result.data = response.data as DimensionBounds;
    } catch (e) {
        result.error = 'Error loading dimension bounds: ' + String(e);
    }

    return result;
};
