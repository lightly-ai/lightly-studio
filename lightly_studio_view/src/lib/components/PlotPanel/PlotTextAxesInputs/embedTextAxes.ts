import { embedText } from '$lib/api/lightly_studio_local';
import type { ProjectionAxes } from '$lib/api/lightly_studio_local/types.gen';
import { toCornerMarkers, type toTextAxes } from './textAxesDraft';

type TextAxes = NonNullable<ReturnType<typeof toTextAxes>>;

// Embeds the texts with the default embedding model of the collection. Returns the axis
// directions embed(positive) - embed(negative), and one marker with its embedding for each
// corner of the plot. Throws an Error with the server message.
export const embedTextAxes = async (
    collectionId: string,
    textAxes: TextAxes
): Promise<{ axes: ProjectionAxes; markers: { label: string; embedding: number[] }[] }> => {
    const { x, y } = textAxes;
    const cornerMarkers = toCornerMarkers(textAxes);
    // One request at a time: the server has one embedding model, so parallel requests wait
    // for each other and only add load.
    const embeddings: number[][] = [];
    for (const text of [
        x.negative,
        x.positive,
        y.negative,
        y.positive,
        ...cornerMarkers.map((marker) => marker.text)
    ]) {
        embeddings.push(await embed(collectionId, text));
    }
    const [xNegative, xPositive, yNegative, yPositive, ...cornerEmbeddings] = embeddings;
    return {
        axes: { x: subtract(xPositive, xNegative), y: subtract(yPositive, yNegative) },
        markers: cornerMarkers.map((marker, index) => ({
            label: marker.label,
            embedding: cornerEmbeddings[index]
        }))
    };
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
