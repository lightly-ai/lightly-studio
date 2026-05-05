import { writable, type Writable } from 'svelte/store';

interface UseFileDropParams {
    /** Called when an image file is accepted from drop, paste, or file input. */
    onFileAccepted: (file: File) => Promise<void>;
    /** Called when user input is invalid (for example non-image drop). */
    onError: (message: string) => void;
}

interface UseFileDropReturn {
    /** `true` while an item is dragged over the drop zone. */
    dragOver: Writable<boolean>;
    /** Enables dropping and marks the drop zone as active. */
    handleDragOver: (event: DragEvent) => void;
    /** Clears drop-zone active state when the dragged item leaves. */
    handleDragLeave: (event: DragEvent) => void;
    /** Accepts a dropped image file and forwards it to `onFileAccepted`. */
    handleDrop: (event: DragEvent) => Promise<void>;
    /** Accepts pasted image data from clipboard and forwards it to `onFileAccepted`. */
    handlePaste: (event: ClipboardEvent) => Promise<void>;
    /** Accepts a selected file from input and resets input value afterward. */
    handleFileSelect: (event: Event) => Promise<void>;
}

/**
 * Centralizes image intake interactions for search UI components.
 */
export function useFileDrop({ onFileAccepted, onError }: UseFileDropParams): UseFileDropReturn {
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

        await onFileAccepted(file);
    };

    const handlePaste = async (event: ClipboardEvent) => {
        const clipboardData = event.clipboardData;
        if (!clipboardData) {
            return;
        }

        for (const file of clipboardData.files ?? []) {
            if (!file.type.startsWith('image/')) {
                continue;
            }

            event.preventDefault();
            await onFileAccepted(file);
            return;
        }

        for (const item of clipboardData.items ?? []) {
            if (!item.type.startsWith('image/')) {
                continue;
            }

            const file = item.getAsFile();
            if (file) {
                event.preventDefault();
                await onFileAccepted(file);
                return;
            }
        }
    };

    const handleFileSelect = async (event: Event) => {
        const target = event.target as HTMLInputElement;
        const file = target.files?.[0];

        try {
            if (file) {
                if (!file.type.startsWith('image/')) {
                    onError('Please drop an image file.');
                } else {
                    await onFileAccepted(file);
                }
            }
        } finally {
            target.value = '';
        }
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
