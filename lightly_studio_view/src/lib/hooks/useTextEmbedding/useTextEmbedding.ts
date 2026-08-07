import { embedText } from '$lib/api/lightly_studio_local';
import { writable, type Writable } from 'svelte/store';

type EmbedSuccessResult = {
    queryText: string;
    embedding: number[];
    collectionId: string;
};

type UseTextEmbeddingParams = {
    /** Returns the target collection id for the embedding endpoint path, read per request. */
    getCollectionId: () => string;
    /** Called with a user-facing error message on embedding failure. */
    onError: (message: string) => void;
    /** Called after successful embedding with trimmed query text and embedding vector. */
    onSuccess: (result: EmbedSuccessResult) => void;
    /**
     * Returns an embedder to use instead of the LightlyStudio backend, or `undefined` to
     * use the backend. Consulted per request, because whether a collection has a
     * customer-hosted embedding service is resolved after this hook is created.
     */
    getEmbed?: () =>
        | ((params: { text: string; collectionId: string }) => Promise<number[]>)
        | undefined;
};

type UseTextEmbeddingReturn = {
    /** `true` while one or more embedding requests are in flight. */
    isEmbedding: Writable<boolean>;
    /** Embeds `text` (after trimming). Empty text is a no-op but invalidates any in-flight request. */
    embed: (text: string) => Promise<void>;
};

/** Handles text embedding state and request retrieval for collection search. */
export function useTextEmbedding({
    getCollectionId,
    onError,
    onSuccess,
    getEmbed
}: UseTextEmbeddingParams): UseTextEmbeddingReturn {
    const isEmbedding = writable(false);
    let latestRequestId = 0;
    let pendingRequests = 0;

    const embed = async (text: string) => {
        const requestId = ++latestRequestId;
        const trimmed = text.trim();
        if (!trimmed) return;

        const collectionId = getCollectionId();
        pendingRequests += 1;
        isEmbedding.set(true);
        try {
            const embedViaService = getEmbed?.();
            const vector = embedViaService
                ? await embedViaService({ text: trimmed, collectionId })
                : await embedViaBackend({ text: trimmed, collectionId });
            if (requestId !== latestRequestId) return;
            onSuccess({ queryText: trimmed, embedding: vector, collectionId });
        } catch (err) {
            if (requestId !== latestRequestId) return;
            const message = err instanceof Error ? err.message : 'Failed to embed text';
            onError(message);
        } finally {
            pendingRequests = Math.max(0, pendingRequests - 1);
            isEmbedding.set(pendingRequests > 0);
        }
    };

    return { isEmbedding, embed };
}

async function embedViaBackend({
    text,
    collectionId
}: {
    text: string;
    collectionId: string;
}): Promise<number[]> {
    const { data, error } = await embedText({
        path: { collection_id: collectionId },
        query: { query_text: text, embedding_model_id: null }
    });
    if (error) {
        const errObj = error as { error?: unknown; message?: string };
        throw new Error(String(errObj.error ?? errObj.message ?? 'Failed to embed text'));
    }
    if (!data) throw new Error('Failed to embed text');
    return data;
}
