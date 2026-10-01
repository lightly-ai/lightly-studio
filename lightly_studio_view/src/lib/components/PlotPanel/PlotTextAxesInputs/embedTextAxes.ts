import { embedText } from '$lib/api/lightly_studio_local';
import type { ProjectionAxes } from '$lib/api/lightly_studio_local/types.gen';
import type { toTextAxes } from './textAxesDraft';

type TextAxes = NonNullable<ReturnType<typeof toTextAxes>>;

// Embeds the four texts with the default embedding model of the collection and returns the
// axis directions embed(positive) - embed(negative). Throws an Error with the server message.
export const embedTextAxes = async (
    collectionId: string,
    textAxes: TextAxes
): Promise<ProjectionAxes> => {
    const [xNegative, xPositive, yNegative, yPositive] = await Promise.all([
        embed(collectionId, textAxes.x.negative),
        embed(collectionId, textAxes.x.positive),
        embed(collectionId, textAxes.y.negative),
        embed(collectionId, textAxes.y.positive)
    ]);
    return { x: subtract(xPositive, xNegative), y: subtract(yPositive, yNegative) };
};

const embed = async (collectionId: string, text: string): Promise<number[]> => {
    const { data, error } = await embedText({
        path: { collection_id: collectionId },
        query: { query_text: text, embedding_model_id: null }
    });
    if (error || !data) {
        const errorObject = error as { error?: unknown; message?: string } | undefined;
        throw new Error(
            String(errorObject?.error ?? errorObject?.message ?? `Failed to embed "${text}"`)
        );
    }
    return data;
};

const subtract = (minuend: number[], subtrahend: number[]): number[] =>
    minuend.map((value, index) => value - subtrahend[index]);
