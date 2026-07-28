import { writable, type Readable } from 'svelte/store';

interface UseExportDownloadReturn {
    isLoading: Readable<boolean>;
    errorMessage: Readable<string>;
    handleDownload: () => Promise<void>;
}

export function useExportDownload(prepare: () => Promise<void>): UseExportDownloadReturn {
    const isLoading = writable(false);
    const errorMessage = writable('');

    const handleDownload = async () => {
        isLoading.set(true);
        errorMessage.set('');
        try {
            await prepare();
        } catch (e) {
            errorMessage.set(`Export failed: ${String(e)}`);
        } finally {
            isLoading.set(false);
        }
    };

    return { isLoading, errorMessage, handleDownload };
}
