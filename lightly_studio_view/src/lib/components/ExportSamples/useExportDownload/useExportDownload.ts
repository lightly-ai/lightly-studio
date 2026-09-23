import { writable, type Readable } from 'svelte/store';

interface UseExportDownloadReturn {
    /** Whether the download preparation is in progress. */
    isLoading: Readable<boolean>;
    /** Error message to display if the download preparation fails, or empty string on success. */
    errorMessage: Readable<string>;
    /** Triggers the download by calling the provided `prepare` function. */
    handleDownload: () => Promise<void>;
}

/**
 * Triggers a file download by creating a temporary anchor element and clicking it.
 * Unlike `window.open`, this does not require user activation and is not blocked by
 * popup blockers when called from an async context.
 */
export function triggerDownload(url: string): void {
    const a = document.createElement('a');
    a.href = url;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

/**
 * Hook that manages the loading and error state for triggering an export download.
 *
 * @param prepare - Async function that performs the actual export preparation (e.g. API call).
 *                  Should throw on failure so the error can be caught and surfaced to the user.
 */
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
