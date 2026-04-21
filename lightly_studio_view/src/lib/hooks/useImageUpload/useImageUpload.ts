import { get, writable } from 'svelte/store';

type UseImageUploadParams = {
    collectionId: string;
    onError: (message: string) => void;
    onUploadSuccess: (result: { fileName: string; embedding: number[] }) => void;
    maxImageSizeMb?: number;
};

/**
 * Handles image-embedding upload lifecycle for collection search.
 *
 * Validates file size, uploads the file to the collection embedding endpoint,
 * manages upload/preview state, and exposes helpers to clear image state with
 * proper object URL cleanup.
 *
 * @param params - Hook configuration.
 * @param params.collectionId - Target collection id used by the upload endpoint.
 * @param params.onError - Called with a user-facing error message when validation or upload fails.
 * @param params.onUploadSuccess - Called with uploaded file metadata and embedding vector.
 * @param params.maxImageSizeMb - Optional maximum allowed image size in MB. Defaults to `50`.
 * @returns Reactive upload state and actions:
 * `activeImage`, `previewUrl`, `isUploading`, `uploadImage`, `clearImage`.
 *
 * @example
 * ```ts
 * const { activeImage, previewUrl, isUploading, uploadImage, clearImage } = useImageUpload({
 *   collectionId,
 *   onError: (message) => toast.error('Error', { description: message }),
 *   onUploadSuccess: ({ fileName, embedding }) => {
 *     setTextEmbedding({ queryText: fileName, embedding });
 *   }
 * });
 * ```
 */
export function useImageUpload({
    collectionId,
    onError,
    onUploadSuccess,
    maxImageSizeMb = 50
}: UseImageUploadParams) {
    const activeImage = writable<string | null>(null);
    const previewUrl = writable<string | null>(null);
    const isUploading = writable(false);

    const maxImageSizeBytes = maxImageSizeMb * 1024 * 1024;

    const clearImage = () => {
        activeImage.set(null);

        const currentPreviewUrl = get(previewUrl);
        if (currentPreviewUrl) {
            URL.revokeObjectURL(currentPreviewUrl);
            previewUrl.set(null);
        }
    };

    const uploadImage = async (file: File) => {
        if (file.size > maxImageSizeBytes) {
            onError(`Image is too large. Maximum size is ${maxImageSizeMb}MB.`);
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        isUploading.set(true);
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

            const embedding = (await response.json()) as number[];

            activeImage.set(file.name);

            const currentPreviewUrl = get(previewUrl);
            if (currentPreviewUrl) {
                URL.revokeObjectURL(currentPreviewUrl);
            }

            previewUrl.set(URL.createObjectURL(file));
            onUploadSuccess({ fileName: file.name, embedding });
        } catch (error: unknown) {
            const message = error instanceof Error ? error.message : 'Failed to upload image';
            onError(message);
        } finally {
            isUploading.set(false);
        }
    };

    return {
        activeImage,
        previewUrl,
        isUploading,
        uploadImage,
        clearImage
    };
}
