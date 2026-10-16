import { embedText } from '$lib/api/lightly_studio_local';
import type { ProjectionAxes } from '$lib/api/lightly_studio_local/types.gen';
import type { toTextAxes } from './textAxesDraft';

type TextAxes = NonNullable<ReturnType<typeof toTextAxes>>;

// Embeds the four texts with the default embedding model of the collection and returns the
// axis directions unit(positive) - unit(negative). Throws an Error with the server message.
export const embedTextAxes = async (
    collectionId: string,
    { x, y }: TextAxes
): Promise<ProjectionAxes> => {
    // One request at a time: the server has one embedding model, so parallel requests wait
    // for each other and only add load.
    const embeddings: number[][] = [];
    for (const text of [x.negative, x.positive, y.negative, y.positive]) {
        // The norm is required for the axes to make sense. With unit vectors p and n, the
        // midpoint (p + n) / 2 projects to (|p|² - |n|²) / 2 = 0 on the axis p - n. So x = 0 is
        // exactly where a sample is as similar to n as to p, and x > 0 where it is more similar
        // to p. Without it, a text with a larger norm (for example with MobileCLIP) moves x = 0
        // away from the midpoint.
        embeddings.push(normalize(await embed(collectionId, text)));
    }
    const [xNegative, xPositive, yNegative, yPositive] = embeddings;
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

const normalize = (vector: number[]): number[] => {
    const norm = Math.hypot(...vector);
    return vector.map((value) => value / norm);
};

const subtract = (minuend: number[], subtrahend: number[]): number[] =>
    minuend.map((value, index) => value - subtrahend[index]);
