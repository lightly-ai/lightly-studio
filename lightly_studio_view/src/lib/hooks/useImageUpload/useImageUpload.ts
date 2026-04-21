import { embedImageFromFileMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation } from '@tanstack/svelte-query';
import { get, writable, type Writable } from 'svelte/store';

type UploadSuccessResult = {
    fileName: string;
    embedding: number[];
};

type UseImageUploadParams = {
    /** Target collection id used by the embedding endpoint path. */
    collectionId: string;
    /** Called with a user-facing error message on validation or upload failure. */
    onError: (message: string) => void;
    /** Called after successful upload with file name and embedding vector. */
    onSuccess: (result: UploadSuccessResult) => void;
    /** Maximum accepted upload size in MB. Defaults to `50`. */
    maxSizeMb?: number;
};

type UseImageUploadReturn = {
    /** Name of the latest successfully uploaded file, `undefined` when not set. */
    imageName: Writable<string | undefined>;
    /** Object URL used to render local preview of the selected image, `undefined` when not set. */
    previewUrl: Writable<string | undefined>;
    /** `true` while an upload request is in flight. */
    isUploading: Writable<boolean>;
    /** Validates and uploads an image file to retrieve its embedding. */
    upload: (file: File) => Promise<void>;
    /** Clears current image state and revokes preview object URL if present. */
    clear: () => void;
};

/** Handles image upload state and embedding retrieval for collection search. */
export function useImageUpload({
    collectionId,
    onError,
    onSuccess,
    maxSizeMb = 50
}: UseImageUploadParams): UseImageUploadReturn {
    const mutation = createMutation(embedImageFromFileMutation());
    // We need to have this subscription to get onSuccess/onError events
    mutation.subscribe(() => undefined);

    const imageName = writable<string | undefined>(undefined);
    const previewUrl = writable<string | undefined>(undefined);
    const isUploading = writable(false);

    const maxImageSizeBytes = maxSizeMb * 1024 * 1024;

    const clear = () => {
        imageName.set(undefined);

        const currentPreviewUrl = get(previewUrl);
        if (currentPreviewUrl) {
            URL.revokeObjectURL(currentPreviewUrl);
        }
        previewUrl.set(undefined);
    };

    const upload = async (file: File) => {
        if (file.size > maxImageSizeBytes) {
            clear();
            onError(`Image is too large. Maximum size is ${maxSizeMb}MB.`);
            return;
        }

        isUploading.set(true);
        try {
            if (!collectionId) {
                throw new Error('Collection ID is not available');
            }

            const embedding = await new Promise<number[]>((resolve, reject) => {
                get(mutation).mutate(
                    {
                        path: {
                            collection_id: collectionId
                        },
                        body: {
                            file
                        }
                    },
                    {
                        onSuccess: (data) => {
                            resolve(data);
                        },
                        onError: (error) => {
                            reject(error);
                        }
                    }
                );
            });

            imageName.set(file.name);

            const currentPreviewUrl = get(previewUrl);
            if (currentPreviewUrl) {
                URL.revokeObjectURL(currentPreviewUrl);
            }

            previewUrl.set(URL.createObjectURL(file));
            onSuccess({ fileName: file.name, embedding });
        } catch (error: unknown) {
            clear();
            const message = error instanceof Error ? error.message : 'Failed to upload image';
            onError(message);
        } finally {
            isUploading.set(false);
        }
    };

    return {
        imageName,
        previewUrl,
        isUploading,
        upload,
        clear
    };
}
