import { createMutation, type MutationOptions } from '@tanstack/svelte-query';
import { derived, get, type Readable } from 'svelte/store';

interface UseFileUploadParams<TResponse, TError, TMutationData> {
    /** TanStack Query mutation options factory function */
    mutationFn: (
        params: Record<string, unknown>
    ) => MutationOptions<TResponse, TError, TMutationData>;
    /** Parameters to pass to the mutation options factory */
    mutationParams?: Record<string, unknown>;
    /** Maximum file size in bytes */
    maxFileSize: number;
    /** Function to build mutation variables from file */
    buildMutationVariables: (file: File) => TMutationData;
    /** Optional callback when upload succeeds */
    onSuccess?: (response: TResponse) => void;
    /** Optional callback when upload fails */
    onError?: (message: string) => void;
    /** Accepted file types (e.g., 'image/', 'video/', '.pdf'). If not provided, all types are accepted */
    acceptedTypes?: string[];
}

interface UseFileUploadReturn {
    /** Whether a file is currently being uploaded */
    isUploading: Readable<boolean>;
    /** Uploads a file using the provided mutation */
    uploadFile: (file: File) => Promise<void>;
}

/**
 * Generic hook to handle file uploads using TanStack Query mutations.
 *
 * @param {UseFileUploadParams} params - Configuration for the file upload
 * @param {Function} params.mutationFn - TanStack Query mutation options factory
 * @param {object} [params.mutationParams] - Parameters to pass to mutation factory
 * @param {number} params.maxFileSize - Maximum allowed file size in bytes
 * @param {Function} params.buildMutationVariables - Function to build mutation variables from file
 * @param {Function} [params.onSuccess] - Optional callback when upload succeeds
 * @param {Function} [params.onError] - Optional callback when upload fails
 *
 * @returns {UseFileUploadReturn} Object containing upload state and functions
 * @returns {Readable<boolean>} isUploading - Reactive store tracking upload state
 * @returns {Function} uploadFile - Function to upload a file
 *
 * @example
 * import { embedImageFromFileMutation } from '$lib/api/...';
 *
 * const { isUploading, uploadFile } = useFileUpload({
 *   mutationFn: embedImageFromFileMutation,
 *   mutationParams: {
 *     path: { collection_id: 'abc123' },
 *     query: { embedding_model_id: 'model-1' }
 *   },
 *   maxFileSize: 50 * 1024 * 1024, // 50MB
 *   buildMutationVariables: (file) => ({
 *     body: { file },
 *     path: { collection_id: 'abc123' }
 *   }),
 *   onSuccess: (embedding) => console.log('Upload successful', embedding),
 *   onError: (message) => toast.error(message)
 * });
 *
 * await uploadFile(imageFile);
 */
export function useFileUpload<TResponse, TError, TMutationData>({
    mutationFn,
    mutationParams = {},
    maxFileSize,
    buildMutationVariables,
    onSuccess,
    onError,
    acceptedTypes
}: UseFileUploadParams<TResponse, TError, TMutationData>): UseFileUploadReturn {
    const mutation = createMutation(mutationFn(mutationParams));

    const isUploading = derived(mutation, ($mutation) => $mutation.isPending);

    function isFileTypeAccepted(file: File): boolean {
        if (!acceptedTypes || acceptedTypes.length === 0) {
            return true;
        }

        return acceptedTypes.some((type) => {
            // Handle MIME type patterns (e.g., 'image/', 'video/')
            if (type.endsWith('/')) {
                return file.type.startsWith(type);
            }
            // Handle file extensions (e.g., '.pdf', '.txt')
            if (type.startsWith('.')) {
                return file.name.toLowerCase().endsWith(type.toLowerCase());
            }
            // Handle full MIME types (e.g., 'image/jpeg', 'video/mp4')
            return file.type === type;
        });
    }

    async function uploadFile(file: File): Promise<void> {
        if (!isFileTypeAccepted(file)) {
            const errorMessage = `File type not accepted. Accepted types: ${acceptedTypes?.join(', ')}`;
            onError?.(errorMessage);
            return;
        }

        if (file.size > maxFileSize) {
            const maxSizeMB = (maxFileSize / (1024 * 1024)).toFixed(0);
            const errorMessage = `File is too large. Maximum size is ${maxSizeMB}MB.`;
            onError?.(errorMessage);
            return;
        }

        try {
            const variables = buildMutationVariables(file);
            const data = await get(mutation).mutateAsync(variables);

            onSuccess?.(data);
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Failed to upload file';
            onError?.(message);
        }
    }

    return {
        isUploading,
        uploadFile
    };
}
