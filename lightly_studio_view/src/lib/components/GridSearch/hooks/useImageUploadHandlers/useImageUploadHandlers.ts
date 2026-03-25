import { writable } from 'svelte/store';

interface UseImageUploadHandlersParams {
    /** Function to upload a file */
    uploadFile: (file: File) => Promise<void>;
    /** Function to handle setting active image name */
    setActiveImage: (name: string | null) => void;
    /** Function to set preview URL */
    setPreviewUrl: (url: string | null) => void;
    /** Function to show error message */
    onError: (message: string) => void;
}

interface UseImageUploadHandlersReturn {
    /** Whether drag is currently over the drop zone */
    dragOver: ReturnType<typeof writable<boolean>>;
    /** Handle drag over event */
    handleDragOver: (e: DragEvent) => void;
    /** Handle drag leave event */
    handleDragLeave: (e: DragEvent) => void;
    /** Handle drop event */
    handleDrop: (e: DragEvent) => Promise<void>;
    /** Handle paste event */
    handlePaste: (e: ClipboardEvent) => Promise<void>;
    /** Handle file selection from input */
    handleFileSelect: (e: Event) => Promise<void>;
}

/**
 * Hook to handle image upload interactions (drag/drop, paste, file select).
 *
 * @param {UseImageUploadHandlersParams} params - Configuration for upload handlers
 * @returns {UseImageUploadHandlersReturn} Object containing drag state and event handlers
 */
export function useImageUploadHandlers({
    uploadFile,
    setActiveImage,
    setPreviewUrl,
    onError
}: UseImageUploadHandlersParams): UseImageUploadHandlersReturn {
    const dragOver = writable(false);

    async function uploadImage(file: File): Promise<void> {
        // Set active image and preview before upload
        setActiveImage(file.name);

        // Create preview URL for the uploaded image
        const previewUrl = URL.createObjectURL(file);
        setPreviewUrl(previewUrl);

        await uploadFile(file);
    }

    function handleDragOver(e: DragEvent): void {
        e.preventDefault();
        dragOver.set(true);
    }

    function handleDragLeave(e: DragEvent): void {
        e.preventDefault();
        dragOver.set(false);
    }

    async function handleDrop(e: DragEvent): Promise<void> {
        e.preventDefault();
        dragOver.set(false);

        if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            if (file.type.startsWith('image/')) {
                await uploadImage(file);
            } else {
                onError('Please drop an image file.');
            }
        }
    }

    async function handlePaste(e: ClipboardEvent): Promise<void> {
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

    async function handleFileSelect(e: Event): Promise<void> {
        const target = e.target as HTMLInputElement;
        if (target.files && target.files.length > 0) {
            await uploadImage(target.files[0]);
        }
        // Reset input
        target.value = '';
    }

    return {
        dragOver,
        handleDragOver,
        handleDragLeave,
        handleDrop,
        handlePaste,
        handleFileSelect
    };
}
