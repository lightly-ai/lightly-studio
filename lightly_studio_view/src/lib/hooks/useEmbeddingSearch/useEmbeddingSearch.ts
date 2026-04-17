import { derived, get } from 'svelte/store';
import { useImageSearch } from '../useImageSearch/useImageSearch';
import { useTextEmbeddingSearch } from '../useTextEmbeddingSearch/useTextEmbeddingSearch';
import type { TextEmbedding } from '$lib/types';
import type { Writable } from 'svelte/store';

/**
 * Combined hook for both image and text embedding search functionality.
 * Manages coordination between the two search modes.
 */
export function useEmbeddingSearch({
    collectionId,
    textEmbedding,
    setTextEmbedding
}: {
    collectionId: string;
    textEmbedding: Writable<TextEmbedding | undefined>;
    setTextEmbedding: (_textEmbedding: TextEmbedding | undefined) => void;
}) {
    // Image search functionality
    const imageSearch = useImageSearch({
        collectionId,
        setTextEmbedding,
        onSearchStateChange: ({ queryText }) => {
            // Sync with text search when image search clears
            textSearch.query_text.set(queryText);
        }
    });

    // Text embedding search functionality
    const textSearch = useTextEmbeddingSearch({
        collectionId,
        textEmbedding,
        setTextEmbedding,
        activeImage: get(imageSearch.activeImage)
    });

    // Combined clear function
    function clearSearch() {
        textSearch.clearSearch();
        imageSearch.clearSearch();
    }

    return {
        // Image search
        dragOver: imageSearch.dragOver,
        activeImage: imageSearch.activeImage,
        previewUrl: imageSearch.previewUrl,
        isUploading: imageSearch.isUploading,
        handleDragOver: imageSearch.handleDragOver,
        handleDragLeave: imageSearch.handleDragLeave,
        handleDrop: imageSearch.handleDrop,
        handlePaste: imageSearch.handlePaste,
        handleFileSelect: imageSearch.handleFileSelect,
        // Text search
        query_text: textSearch.query_text,
        submittedQueryText: textSearch.submittedQueryText,
        handleKeyDown: textSearch.handleKeyDown,
        // Combined
        clearSearch
    };
}
