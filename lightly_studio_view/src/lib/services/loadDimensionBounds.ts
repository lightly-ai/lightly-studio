import { client } from './collection';
import type { LoadResult } from './types';

export type DimensionBounds = {
    min_width: number;
    max_width: number;
    min_height: number;
    max_height: number;
};

type LoadDimensionBoundsParams = {
    collection_id: string;
    annotation_label_ids?: string[];
};

export const loadDimensionBounds = async ({
    collection_id,
    annotation_label_ids
}: LoadDimensionBoundsParams): Promise<LoadResult<DimensionBounds | undefined>> => {
    const result: LoadResult<DimensionBounds | undefined> = {
        data: undefined,
        error: undefined
    };

    try {
        const response = await client.GET('/api/collections/{collection_id}/images/dimensions', {
            params: {
                path: {
                    collection_id
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
