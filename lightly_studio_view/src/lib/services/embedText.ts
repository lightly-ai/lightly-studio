import type { components } from '$lib/schema';
import { client } from './dataset';
import type { LoadResult } from './types';

type EmbedTextParams = {
    query_text: string;
    model_id?: string;
};
type EmbedTextResponse = components['schemas']['TextEmbedding'];
export type EmbedResult = LoadResult<EmbedTextResponse>;

export const embedText = async ({
    query_text = '',
    model_id = ''
}: EmbedTextParams): Promise<EmbedResult> => {
    const result: EmbedResult = {
        data: { embedding: [], model_id: '' },
        error: undefined
    };
    try {
        const response = await client.GET('/api/text_embedding/embed_text', {
            params: {
                query: {
                    query_text,
                    model_id
                }
            }
        });
        if (response.error) {
            throw new Error(JSON.stringify(response.error, null, 2));
        }

        if (!response.data) {
            throw new Error('No data');
        }
        result.data = response.data;
    } catch (e) {
        result.error = 'Error creating text embedding: ' + String(e);
    }

    return result;
};
