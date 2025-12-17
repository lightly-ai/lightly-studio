import type { DatasetProgress, ProgressUpdate } from '$lib/components/DatasetProgress/types';
import { client } from '$lib/services/dataset';

/**
 * Fetch progress for a specific dataset
 * TODO: Replace with actual API endpoint when backend is ready
 */
export async function fetchDatasetProgress(dataset_id: string): Promise<DatasetProgress | null> {
    try {
        // TODO: Replace this with actual API call
        // const response = await client.GET('/api/datasets/{dataset_id}/progress', {
        //     params: { path: { dataset_id } }
        // });
        //
        // if (response.error) {
        //     throw new Error(`Failed to fetch progress: ${JSON.stringify(response.error)}`);
        // }
        //
        // return response.data;

        // Mock implementation for now
        return mockFetchProgress(dataset_id);
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
            console.error(`Error polling progress (attempt ${consecutiveErrors}/${maxRetries}):`, error);

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

// ============================================================================
// Mock implementation - remove when backend is ready
// ============================================================================

let mockProgress: Record<string, DatasetProgress> = {};

function mockFetchProgress(dataset_id: string): DatasetProgress {
    if (!mockProgress[dataset_id]) {
        mockProgress[dataset_id] = {
            dataset_id,
            state: 'pending',
            current: 0,
            total: 100,
            message: 'Waiting to start...',
            error: null,
            updated_at: new Date().toISOString()
        };
    }

    // Simulate progress
    const current = mockProgress[dataset_id];
    if (current.state !== 'ready' && current.state !== 'error') {
        const increment = Math.floor(Math.random() * 10) + 1;
        const newCurrent = Math.min(current.current + increment, current.total);

        let newState = current.state;
        let message = current.message;

        if (newCurrent < current.total * 0.5) {
            newState = 'indexing';
            message = `Indexing samples... ${newCurrent}/${current.total}`;
        } else if (newCurrent < current.total) {
            newState = 'embedding';
            message = `Generating embeddings... ${newCurrent}/${current.total}`;
        } else {
            newState = 'ready';
            message = 'Dataset is ready!';
        }

        mockProgress[dataset_id] = {
            ...current,
            state: newState,
            current: newCurrent,
            message,
            updated_at: new Date().toISOString()
        };
    }

    return mockProgress[dataset_id];
}

/**
 * Mock function to reset progress (for testing)
 */
export function resetMockProgress(dataset_id: string) {
    delete mockProgress[dataset_id];
}

/**
 * Mock function to set progress state (for testing)
 */
export function setMockProgress(dataset_id: string, progress: Partial<DatasetProgress>) {
    mockProgress[dataset_id] = {
        dataset_id,
        state: 'pending',
        current: 0,
        total: 100,
        message: '',
        error: null,
        updated_at: new Date().toISOString(),
        ...mockProgress[dataset_id],
        ...progress
    };
}
