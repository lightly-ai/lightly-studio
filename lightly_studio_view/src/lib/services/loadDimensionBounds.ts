import { getImageDimensions } from '$lib/api/lightly_studio_local';
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

const isDimensionBounds = (value: unknown): value is DimensionBounds => {
    if (!value || typeof value !== 'object') return false;

    const bounds = value as Record<keyof DimensionBounds, unknown>;
    return (
        typeof bounds.min_width === 'number' &&
        typeof bounds.max_width === 'number' &&
        typeof bounds.min_height === 'number' &&
        typeof bounds.max_height === 'number'
    );
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
        const response = await getImageDimensions({
            path: {
                collection_id
            },
            query: {
                annotation_label_ids
            }
        });

        if (response.error) {
            throw new Error(JSON.stringify(response.error, null, 2));
        }

        if (!isDimensionBounds(response.data)) {
            throw new Error('No dimension bounds data');
        }

        result.data = response.data;
    } catch (e) {
        result.error = 'Error loading dimension bounds: ' + String(e);
    }

    return result;
};
