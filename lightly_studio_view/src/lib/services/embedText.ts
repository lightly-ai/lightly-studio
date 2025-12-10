import { client } from './dataset';
import type { components } from '$lib/schema';
import type { LoadResult } from './types';

type EmbedTextParams = {
    query_text: string;
    embedding_model_id: string | null;
    sample_type?: 'video' | 'video_frame' | 'image' | 'annotation' | 'caption' | null;
};
type EmbedTextResponse = components['schemas']['TextEmbedding'];
export type EmbedResult = LoadResult<EmbedTextResponse>;

export const embedText = async ({
    query_text = '',
    embedding_model_id = null,
    sample_type = null
}: EmbedTextParams): Promise<EmbedResult> => {
    const result: EmbedResult = {
        data: { embedding: [], embedding_model_id: '' },
        error: undefined
    };
    try {
        const response = await client.GET('/api/text_embedding/embed_text', {
            params: {
                query: {
                    query_text,
                    embedding_model_id,
                    sample_type
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
