import { writable } from 'svelte/store';

type UseFileDropParams = {
    onFile: (file: File) => Promise<void> | void;
    onError: (message: string) => void;
};

/**
 * Centralizes image intake interactions for search UI components.
 *
 * Handles drag-and-drop, clipboard paste, and file input selection, while
 * exposing reactive drag-over state for UI feedback and delegating accepted
 * files to the provided upload callback.
 *
 * @param params - Hook configuration.
 * @param params.onFile - Called when an image file is accepted from any input source.
 * @param params.onError - Called when user input is invalid (for example non-image drop).
 * @returns Handlers and state used by the search component:
 * `dragOver`, `handleDragOver`, `handleDragLeave`, `handleDrop`, `handlePaste`, `handleFileSelect`.
 *
 * @example
 * ```ts
 * const {
 *   dragOver,
 *   handleDragOver,
 *   handleDragLeave,
 *   handleDrop,
 *   handlePaste,
 *   handleFileSelect
 * } = useFileDrop({
 *   onFile: uploadImage,
 *   onError: (message) => toast.error('Error', { description: message })
 * });
 * ```
 */
export function useFileDrop({ onFile, onError }: UseFileDropParams) {
    const dragOver = writable(false);

    const handleDragOver = (event: DragEvent) => {
        event.preventDefault();
        dragOver.set(true);
    };

    const handleDragLeave = (event: DragEvent) => {
        event.preventDefault();
        dragOver.set(false);
    };

    const handleDrop = async (event: DragEvent) => {
        event.preventDefault();
        dragOver.set(false);

        const file = event.dataTransfer?.files?.[0];
        if (!file) {
            return;
        }

        if (!file.type.startsWith('image/')) {
            onError('Please drop an image file.');
            return;
        }

        await onFile(file);
    };

    const handlePaste = async (event: ClipboardEvent) => {
        const clipboardData = event.clipboardData;
        if (!clipboardData) {
            return;
        }

        const fileFromFiles = clipboardData.files?.[0];
        if (fileFromFiles && fileFromFiles.type.startsWith('image/')) {
            event.preventDefault();
            await onFile(fileFromFiles);
            return;
        }

        for (const item of clipboardData.items ?? []) {
            if (!item.type.startsWith('image/')) {
                continue;
            }

            const file = item.getAsFile();
            if (file) {
                event.preventDefault();
                await onFile(file);
                return;
            }
        }
    };

    const handleFileSelect = async (event: Event) => {
        const target = event.target as HTMLInputElement;
        const file = target.files?.[0];

        if (file) {
            await onFile(file);
        }

        target.value = '';
    };

    return {
        dragOver,
        handleDragOver,
        handleDragLeave,
        handleDrop,
        handlePaste,
        handleFileSelect
    };
}
