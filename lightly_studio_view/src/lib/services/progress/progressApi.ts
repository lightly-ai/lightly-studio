import type { DatasetProgress, ProgressUpdate } from '$lib/components/DatasetProgress/types';
import { client } from '$lib/services/dataset';

/**
 * Convert status counts response to progress information
 */
function convertStatusToProgress(
    dataset_id: string,
    status_metadata: Record<string, number>,
    status_embeddings: Record<string, number>
): DatasetProgress {
    // Calculate totals
    const totalMetadata = Object.values(status_metadata).reduce((sum, count) => sum + count, 0);
    const totalEmbeddings = Object.values(status_embeddings).reduce(
        (sum, count) => sum + count,
        0
    );

    // Count completed items
    const completedMetadata =
        (status_metadata['success'] || 0) + (status_metadata['skipped'] || 0);
    const completedEmbeddings =
        (status_embeddings['success'] || 0) + (status_embeddings['skipped'] || 0);

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
}

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

        return convertStatusToProgress(
            dataset_id,
            response.data.status_metadata,
            response.data.status_embeddings
        );
    } catch (error) {
        console.error('Error fetching dataset progress:', error);
        throw error;
    }
}

/**
 * Connect to WebSocket for real-time progress updates
 * @param dataset_id - The dataset ID to monitor progress for
 * @param onUpdate - Callback function called when progress updates
 * @param options - Additional options for WebSocket behavior
 * @returns Cleanup function to close WebSocket connection
 */
export function connectProgressWebSocket(
    dataset_id: string,
    onUpdate: (progress: DatasetProgress) => void,
    options?: {
        interval?: number;
        maxRetries?: number;
        onError?: (error: Error) => void;
        onClose?: () => void;
    }
): () => void {
    const interval = options?.interval ?? 2000;
    const maxRetries = options?.maxRetries ?? 5;
    let ws: WebSocket | null = null;
    let reconnectAttempts = 0;
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
    let isClosed = false;

    const connect = () => {
        if (isClosed) return;

        // Construct WebSocket URL based on current location
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/datasets/${dataset_id}/progress`;

        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            reconnectAttempts = 0;
            // Send configuration to server
            ws?.send(JSON.stringify({ interval: interval / 1000 }));
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                if (data.error) {
                    console.error('WebSocket error:', data.error);
                    options?.onError?.(new Error(data.error));
                    return;
                }

                const progress = convertStatusToProgress(
                    dataset_id,
                    data.status_metadata,
                    data.status_embeddings
                );

                onUpdate(progress);

                // Close connection if dataset is ready or in error state
                if (progress.state === 'ready' || progress.state === 'error') {
                    cleanup();
                }
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        ws.onclose = () => {
            if (isClosed) {
                options?.onClose?.();
                return;
            }

            // Attempt to reconnect with exponential backoff
            if (reconnectAttempts < maxRetries) {
                reconnectAttempts++;
                const backoffDelay = Math.min(1000 * Math.pow(2, reconnectAttempts - 1), 30000);
                console.log(`Reconnecting in ${backoffDelay}ms (attempt ${reconnectAttempts}/${maxRetries})`);

                reconnectTimeout = setTimeout(() => {
                    connect();
                }, backoffDelay);
            } else {
                console.error('Max reconnection attempts reached');
                options?.onError?.(new Error('Failed to connect after multiple attempts'));
                options?.onClose?.();
            }
        };
    };

    const cleanup = () => {
        isClosed = true;

        if (reconnectTimeout) {
            clearTimeout(reconnectTimeout);
            reconnectTimeout = null;
        }

        if (ws) {
            ws.close();
            ws = null;
        }
    };

    // Start connection
    connect();

    // Return cleanup function
    return cleanup;
}

/**
 * Start progress polling for a dataset with automatic retry on errors
 * @deprecated Use connectProgressWebSocket instead for real-time updates
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
