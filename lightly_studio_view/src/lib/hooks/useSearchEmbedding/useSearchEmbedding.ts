import { useImageUpload } from '$lib/hooks/useImageUpload/useImageUpload';
import { useTextEmbedding } from '$lib/hooks/useTextEmbedding/useTextEmbedding';
import type { TextEmbedding } from '$lib/hooks/useGlobalStorage';
import { toast } from 'svelte-sonner';
import { derived, readonly, type Readable, type Writable } from 'svelte/store';

export type SearchEmbeddingImage = {
    name: string;
    previewUrl: string;
};

interface Params {
    /** Target collection id used by the embedding endpoints. */
    collectionId: string;
    /** External writable that receives the resulting embedding. */
    embedding: Writable<TextEmbedding | undefined>;
}

interface Return {
    /** Read-only view of the embedding store. */
    embedding: Readable<TextEmbedding | undefined>;
    /** Image chip state (name + preview URL) when an image search is active. */
    image: Readable<SearchEmbeddingImage | undefined>;
    /** True while a text or image embedding request is in flight. */
    isPending: Readable<boolean>;
    /** Embed `text` and update the embedding store. Empty or whitespace-only input clears it. */
    setText: (text: string) => Promise<void>;
    /** Upload `file`, embed it, and update the embedding/image stores. */
    setImage: (file: File) => Promise<void>;
    /** Set a precomputed embedding (e.g. stored annotation vector for drag-to-search). */
    setEmbedding: (params: {
        queryText: string;
        embedding: number[];
        imagePreview?: { name: string; previewUrl: string };
    }) => void;
    /** Reset both image and embedding state. */
    clear: () => void;
    /** Surface a user-visible error (used by external callers like grid drop). */
    onError: (message: string) => void;
}

export function useSearchEmbedding({ collectionId, embedding }: Params): Return {
    const onError = (message: string) => {
        toast.error('Error', { description: message });
    };

    const upload = useImageUpload({
        collectionId,
        onError,
        onSuccess: ({ fileName, embedding: vector }) => {
            embedding.set({ queryText: fileName, embedding: vector });
        }
    });

    const text = useTextEmbedding({
        collectionId,
        onError,
        onSuccess: ({ queryText, embedding: vector }) => {
            embedding.set({ queryText, embedding: vector });
        }
    });

    const image: Readable<SearchEmbeddingImage | undefined> = derived(
        [upload.imageName, upload.previewUrl],
        ([$name, $url]) => ($name && $url ? { name: $name, previewUrl: $url } : undefined)
    );

    const isPending: Readable<boolean> = derived(
        [text.isEmbedding, upload.isUploading],
        ([$embeddingText, $uploading]) => $embeddingText || $uploading
    );

    const setText = async (input: string) => {
        upload.clear();
        if (!input.trim()) {
            embedding.set(undefined);
        }
        await text.embed(input);
    };

    const setImage = async (file: File) => {
        await upload.upload(file);
    };

    const setEmbedding = ({
        queryText,
        embedding: vector,
        imagePreview
    }: {
        queryText: string;
        embedding: number[];
        imagePreview?: { name: string; previewUrl: string };
    }) => {
        upload.clear();
        if (imagePreview) {
            // Preview URL is owned by the annotation tile; do not revoke on clear.
            upload.setPreview(imagePreview.name, imagePreview.previewUrl, false);
        }
        embedding.set({ queryText, embedding: vector });
    };

    const clear = () => {
        upload.clear();
        embedding.set(undefined);
    };

    return {
        embedding: readonly(embedding),
        image: readonly(image),
        isPending: readonly(isPending),
        setText,
        setImage,
        setEmbedding,
        clear,
        onError
    };
}
