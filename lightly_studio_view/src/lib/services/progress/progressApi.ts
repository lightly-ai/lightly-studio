import type { DatasetProgress, ProgressUpdate } from '$lib/components/DatasetProgress/types';
import { client } from '$lib/services/dataset';

/**
 * Fetch progress for a specific dataset using the status-counts endpoint
 */
export async function fetchDatasetProgress(dataset_id: string): Promise<DatasetProgress | null> {
    try {
        const response = await client.GET('/api/datasets/{dataset_id}/images-status-counts', {
            params: { path: { dataset_id } }
        });

        if (!response || response.error) {
            throw new Error(`Failed to fetch progress: ${JSON.stringify(response?.error)}`);
        }

        if (!response.data) {
            return null;
        }

        // Convert status counts to progress information
        const { status_metadata, status_embeddings } = response.data;

        console.log('Status Metadata:', status_metadata);
        // Calculate totals
        const totalMetadata = Object.values(status_metadata).reduce((sum, count) => sum + count, 0);
        const totalEmbeddings = Object.values(status_embeddings).reduce(
            (sum, count) => sum + count,
            0
        );

        // Count completed items
        const completedMetadata =
            (status_metadata['ready'] || 0) + (status_metadata['skipped'] || 0);
        const completedEmbeddings =
            (status_embeddings['ready'] || 0) + (status_embeddings['skipped'] || 0);

        // Determine state and progress
        let state: DatasetProgress['state'] = 'pending';
        let current = 0;
        let total = totalMetadata + totalEmbeddings;
        let message = 'Initializing...';

        if (status_metadata['error'] > 0 || status_embeddings['error'] > 0) {
            state = 'error';
            message = 'Processing failed for some images';
        } else if (
            completedMetadata === totalMetadata &&
            completedEmbeddings === totalEmbeddings &&
            total > 0
        ) {
            state = 'ready';
            current = total;
            message = 'Dataset is ready!';
        } else if (completedMetadata < totalMetadata || status_metadata['processing'] > 0) {
            state = 'indexing';
            current = completedMetadata;
            message = `Indexing samples... ${completedMetadata}/${totalMetadata}`;
        } else if (completedEmbeddings < totalEmbeddings || status_embeddings['processing'] > 0) {
            state = 'embedding';
            current = completedMetadata + completedEmbeddings;
            message = `Generating embeddings... ${completedEmbeddings}/${totalEmbeddings}`;
        }

        return {
            dataset_id,
            state,
            current,
            total,
            message,
            error: state === 'error' ? message : null,
            updated_at: new Date().toISOString()
        };
    } catch (error) {
        console.error('Error fetching dataset progress:', error);
        throw error;
    }
}

/**
 * Start progress polling for a dataset with automatic retry on errors
 * @param dataset_id - The dataset ID to poll progress for
 * @param onUpdate - Callback function called when progress updates
 * @param interval - Polling interval in milliseconds (default: 2000ms)
 * @param options - Additional options for polling behavior
 * @returns Cleanup function to stop polling
 */
export function startProgressPolling(
    dataset_id: string,
    onUpdate: (progress: DatasetProgress) => void,
    interval: number = 2000,
    options?: {
        maxRetries?: number;
        onError?: (error: Error) => void;
    }
): () => void {
    let isActive = true;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;
    let consecutiveErrors = 0;
    const maxRetries = options?.maxRetries ?? 5;

    const poll = async () => {
        if (!isActive) return;

        try {
            const progress = await fetchDatasetProgress(dataset_id);
            if (progress) {
                // Reset error count on successful fetch
                consecutiveErrors = 0;

                onUpdate(progress);

                // Stop polling if dataset is ready or in error state
                if (progress.state === 'ready' || progress.state === 'error') {
                    cleanup();
                    return;
                }
            }
        } catch (error) {
            consecutiveErrors++;
            console.error(
                `Error polling progress (attempt ${consecutiveErrors}/${maxRetries}):`,
                error
            );

            if (consecutiveErrors >= maxRetries) {
                console.error('Max polling retries reached, stopping polling');
                options?.onError?.(new Error('Failed to fetch progress after multiple attempts'));
                cleanup();
                return;
            }

            // Use exponential backoff for retries
            const backoffInterval = Math.min(interval * Math.pow(2, consecutiveErrors - 1), 30000);
            if (isActive) {
                timeoutId = setTimeout(poll, backoffInterval);
            }
            return;
        }

        if (isActive) {
            timeoutId = setTimeout(poll, interval);
        }
    };

    const cleanup = () => {
        isActive = false;
        if (timeoutId) {
            clearTimeout(timeoutId);
            timeoutId = null;
        }
    };

    // Start polling
    poll();

    // Return cleanup function
    return cleanup;
}
