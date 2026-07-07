import { embedImageFromFileMutation } from '$lib/api/lightly_studio_local/@tanstack/svelte-query.gen';
import { createMutation } from '@tanstack/svelte-query';
import { get, readonly, writable, type Readable } from 'svelte/store';

type UploadSuccessResult = {
    fileName: string;
    embedding: number[];
};

type UseImageUploadParams = {
    /** Returns the target collection id for the embedding endpoint path, read per upload. */
    getCollectionId: () => string;
    /** Called with a user-facing error message on validation or upload failure. */
    onError: (message: string) => void;
    /** Called after successful upload with file name and embedding vector. */
    onSuccess: (result: UploadSuccessResult) => void;
    /** Maximum accepted upload size in MB. Defaults to `50`. */
    maxSizeMb?: number;
};

type UseImageUploadReturn = {
    /** Name of the latest successfully uploaded file, `undefined` when not set. */
    imageName: Readable<string | undefined>;
    /** Object URL used to render local preview of the selected image, `undefined` when not set. */
    previewUrl: Readable<string | undefined>;
    /** `true` while an upload request is in flight. */
    isUploading: Readable<boolean>;
    /** Validates and uploads an image file to retrieve its embedding. */
    upload: (file: File) => Promise<void>;
    /** Show a preview without uploading (e.g. annotation crop owned elsewhere). */
    setPreview: (fileName: string, previewUrl: string, revokeOnClear?: boolean) => void;
    /** Clears current image state and revokes preview object URL if present. */
    clear: () => void;
};

/** Handles image upload state and embedding retrieval for collection search. */
export function useImageUpload({
    getCollectionId,
    onError,
    onSuccess,
    maxSizeMb = 50
}: UseImageUploadParams): UseImageUploadReturn {
    const mutation = createMutation(() => embedImageFromFileMutation());

    const imageName = writable<string | undefined>(undefined);
    const previewUrl = writable<string | undefined>(undefined);
    const isUploading = writable(false);
    let previewOwned = false;

    const maxImageSizeBytes = maxSizeMb * 1024 * 1024;

    const clear = () => {
        imageName.set(undefined);

        const currentPreviewUrl = get(previewUrl);
        if (currentPreviewUrl && previewOwned) {
            URL.revokeObjectURL(currentPreviewUrl);
        }
        previewUrl.set(undefined);
        previewOwned = false;
    };

    const setPreview = (fileName: string, url: string, revokeOnClear = true) => {
        imageName.set(fileName);

        const currentPreviewUrl = get(previewUrl);
        if (currentPreviewUrl && previewOwned) {
            URL.revokeObjectURL(currentPreviewUrl);
        }

        previewUrl.set(url);
        previewOwned = revokeOnClear;
    };

    const upload = async (file: File) => {
        if (file.size > maxImageSizeBytes) {
            clear();
            onError(`Image is too large. Maximum size is ${maxSizeMb}MB.`);
            return;
        }

        isUploading.set(true);
        try {
            const collectionId = getCollectionId();
            if (!collectionId) {
                throw new Error('Collection ID is not available');
            }

            const embedding = await new Promise<number[]>((resolve, reject) => {
                mutation.mutate(
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

            setPreview(file.name, URL.createObjectURL(file));
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
        imageName: readonly(imageName),
        previewUrl: readonly(previewUrl),
        isUploading: readonly(isUploading),
        upload,
        setPreview,
        clear
    };
}
