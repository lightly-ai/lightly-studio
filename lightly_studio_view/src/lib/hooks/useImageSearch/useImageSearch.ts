import { writable } from 'svelte/store';
import { toast } from 'svelte-sonner';
import type { TextEmbedding } from '$lib/types';

const MAX_IMAGE_SIZE_MB = 50;
const MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024;

/**
 * Hook to manage image-based embedding search.
 * Handles image upload via drag-and-drop, paste, or file selection.
 */
export function useImageSearch({
    collectionId,
    setTextEmbedding,
    onSearchStateChange
}: {
    collectionId: string;
    setTextEmbedding: (_textEmbedding: TextEmbedding | undefined) => void;
    onSearchStateChange?: (state: { queryText: string; submittedQueryText: string }) => void;
}) {
    const dragOverStore = writable(false);
    const activeImageStore = writable<string | null>(null);
    const previewUrlStore = writable<string | null>(null);
    const isUploadingStore = writable(false);

    let currentPreviewUrl: string | null = null;

    const setError = (errorMessage: string) => {
        toast.error('Error', { description: errorMessage });
    };

    function handleDragOver(e: DragEvent) {
        e.preventDefault();
        dragOverStore.set(true);
    }

    function handleDragLeave(e: DragEvent) {
        e.preventDefault();
        dragOverStore.set(false);
    }

    async function handleDrop(e: DragEvent) {
        e.preventDefault();
        dragOverStore.set(false);
        if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            if (file.type.startsWith('image/')) {
                await uploadImage(file);
            } else {
                setError('Please drop an image file.');
            }
        }
    }

    async function handlePaste(e: ClipboardEvent) {
        const clipboardData = e.clipboardData;
        if (!clipboardData) return;

        // Check clipboardData.files first (most common case)
        if (clipboardData.files && clipboardData.files.length > 0) {
            const file = clipboardData.files[0];
            if (file.type.startsWith('image/')) {
                e.preventDefault();
                await uploadImage(file);
                return;
            }
        }

        // Fallback: check clipboardData.items (screenshots, images copied from web)
        const items = clipboardData.items;
        if (items) {
            for (const item of items) {
                if (item.type.startsWith('image/')) {
                    const file = item.getAsFile();
                    if (file) {
                        e.preventDefault();
                        await uploadImage(file);
                        return;
                    }
                }
            }
        }
    }

    async function handleFileSelect(e: Event) {
        const target = e.target as HTMLInputElement;
        if (target.files && target.files.length > 0) {
            await uploadImage(target.files[0]);
        }
        // Reset input
        target.value = '';
    }

    async function uploadImage(file: File) {
        if (file.size > MAX_IMAGE_SIZE_BYTES) {
            setError(`Image is too large. Maximum size is ${MAX_IMAGE_SIZE_MB}MB.`);
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        isUploadingStore.set(true);
        try {
            if (!collectionId) {
                throw new Error('Collection ID is not available');
            }
            const response = await fetch(
                `/api/image_embedding/from_file/for_collection/${collectionId}`,
                {
                    method: 'POST',
                    body: formData
                }
            );

            if (!response.ok) {
                throw new Error(`Error uploading image: ${response.statusText}`);
            }

            const embedding = await response.json();

            // Clear text search state
            if (onSearchStateChange) {
                onSearchStateChange({ queryText: '', submittedQueryText: '' });
            }
            activeImageStore.set(file.name);

            // Create preview URL for the uploaded image
            if (currentPreviewUrl) {
                URL.revokeObjectURL(currentPreviewUrl);
            }
            currentPreviewUrl = URL.createObjectURL(file);
            previewUrlStore.set(currentPreviewUrl);

            setTextEmbedding({
                queryText: file.name,
                embedding: embedding
            });
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Failed to upload image';
            setError(message);
        } finally {
            isUploadingStore.set(false);
        }
    }

    function clearSearch() {
        activeImageStore.set(null);
        if (currentPreviewUrl) {
            URL.revokeObjectURL(currentPreviewUrl);
            currentPreviewUrl = null;
        }
        previewUrlStore.set(null);
        setTextEmbedding(undefined);

        if (onSearchStateChange) {
            onSearchStateChange({ queryText: '', submittedQueryText: '' });
        }
    }

    return {
        dragOver: dragOverStore,
        activeImage: activeImageStore,
        previewUrl: previewUrlStore,
        isUploading: isUploadingStore,
        handleDragOver,
        handleDragLeave,
        handleDrop,
        handlePaste,
        handleFileSelect,
        clearSearch
    };
}
