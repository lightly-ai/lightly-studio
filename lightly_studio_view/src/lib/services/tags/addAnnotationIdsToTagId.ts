import { client } from '../dataset';
import type { LoadResult, AnnotationIdsBody } from '../types';

type AddannotationIdsToTagIdResult = LoadResult<boolean | undefined>;
type AddannotationIdsToTagIdParams = {
    dataset_id: string;
    tag_id: string;
    annotationIdsBody: AnnotationIdsBody;
};

// TODO: properly abstract each endpoint and use the types of client to make the request
export const addAnnotationIdsToTagId = async ({
    dataset_id,
    tag_id,
    annotationIdsBody
}: AddannotationIdsToTagIdParams): Promise<AddannotationIdsToTagIdResult> => {
    const result: AddannotationIdsToTagIdResult = { data: undefined, error: undefined };
    try {
        const response = await client.POST(
            '/api/datasets/{dataset_id}/tags/{tag_id}/add/annotations',
            {
                params: {
                    path: {
                        dataset_id,
                        tag_id
                    }
                },
                body: annotationIdsBody
            }
        );

        if (response.error) {
            throw new Error(JSON.stringify(response.error, null, 2));
        }
        if (!response.data) {
            throw new Error('No data');
        }
        result.data = response.data;
    } catch (e) {
        result.error = 'Error assigning annotationIds to a tag: ' + String(e);
    }

    return result;
};
