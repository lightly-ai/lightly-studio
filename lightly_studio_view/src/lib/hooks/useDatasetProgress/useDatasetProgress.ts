import { writable, readonly, get, type Readable } from 'svelte/store';
import type { DatasetProgress, DatasetProgressState } from '$lib/components/DatasetProgress/types';
import { startProgressPolling } from '$lib/services/progress/progressApi';
import { createProgressWebSocket } from '$lib/services/progress/websocket';

interface UseDatasetProgressOptions {
    dataset_id: string;
    mode?: 'polling' | 'websocket' | 'manual';
    pollingInterval?: number;
}

interface UseDatasetProgressReturn {
    progress: Readable<DatasetProgress | null>;
    startProgress: () => void;
    stopProgress: () => void;
    updateProgress: (current: number, total: number, message?: string) => void;
    setError: (error: string) => void;
    setReady: () => void;
    isLoading: Readable<boolean>;
    error: Readable<string | null>;
}

// Global store to track progress for all datasets
const progressByDataset = writable<Record<string, DatasetProgress>>({});

export function useDatasetProgress(options: UseDatasetProgressOptions): UseDatasetProgressReturn {
    const { dataset_id, mode = 'polling', pollingInterval = 2000 } = options;
    const isLoading = writable(false);
    const error = writable<string | null>(null);

    // Derived store for this specific dataset's progress
    const progress = writable<DatasetProgress | null>(null);

    // Subscribe to global store and filter for this dataset
    progressByDataset.subscribe(($progressByDataset) => {
        progress.set($progressByDataset[dataset_id] || null);
    });

    let cleanupConnection: (() => void) | null = null;

    const updateProgressState = (updates: Partial<DatasetProgress>) => {
        progressByDataset.update(($progressByDataset) => {
            const current = $progressByDataset[dataset_id] || {
                dataset_id,
                state: 'pending' as DatasetProgressState,
                current: 0,
                total: 0,
                message: '',
                error: null,
                updated_at: new Date().toISOString()
            };

            return {
                ...$progressByDataset,
                [dataset_id]: {
                    ...current,
                    ...updates,
                    updated_at: new Date().toISOString()
                }
            };
        });
    };

    const handleProgressUpdate = (progressData: DatasetProgress) => {
        updateProgressState(progressData);

        if (progressData.state === 'ready') {
            isLoading.set(false);
        }

        if (progressData.error) {
            error.set(progressData.error);
        }
    };

    const startProgress = () => {
        isLoading.set(true);
        error.set(null);

        // Stop any existing connection
        stopProgress();

        if (mode === 'websocket') {
            // Use WebSocket for real-time updates
            cleanupConnection = createProgressWebSocket({
                dataset_id,
                onUpdate: handleProgressUpdate,
                onError: (err) => {
                    console.error('WebSocket error, falling back to polling:', err);
                    error.set(err.message);
                    // Fallback to polling on WebSocket error
                    startPolling();
                },
                onConnect: () => {
                    console.log('WebSocket connected for progress updates');
                },
                onDisconnect: () => {
                    console.log('WebSocket disconnected');
                }
            });
        } else if (mode === 'polling') {
            startPolling();
        }
        // In 'manual' mode, do nothing - user will call updateProgress manually
    };

    const startPolling = () => {
        cleanupConnection = startProgressPolling(
            dataset_id,
            handleProgressUpdate,
            pollingInterval,
            {
                maxRetries: 5,
                onError: (err) => {
                    error.set(err.message);
                    isLoading.set(false);
                }
            }
        );
    };

    const stopProgress = () => {
        if (cleanupConnection) {
            cleanupConnection();
            cleanupConnection = null;
        }
    };

    const updateProgress = (current: number, total: number, message?: string) => {
        // Determine state based on progress
        let state: DatasetProgressState = 'indexing';
        if (current >= total * 0.5) {
            state = 'embedding';
        }
        if (current >= total) {
            state = 'ready';
            isLoading.set(false);
        }

        updateProgressState({
            state,
            current,
            total,
            message: message || (state === 'indexing' ? 'Indexing samples...' : 'Generating embeddings...')
        });
    };

    const setError = (errorMessage: string) => {
        isLoading.set(false);
        error.set(errorMessage);
        updateProgressState({
            state: 'error',
            error: errorMessage
        });
        stopProgress();
    };

    const setReady = () => {
        isLoading.set(false);
        updateProgressState({
            state: 'ready',
            current: get(progress)?.total || 100,
            message: 'Dataset is ready!'
        });
        stopProgress();
    };

    return {
        progress: readonly(progress),
        startProgress,
        stopProgress,
        updateProgress,
        setError,
        setReady,
        isLoading: readonly(isLoading),
        error: readonly(error)
    };
}

// Mock data generator for testing
export function generateMockProgress(dataset_id: string): DatasetProgress {
    const states: DatasetProgressState[] = ['pending', 'indexing', 'embedding', 'ready'];
    const randomState = states[Math.floor(Math.random() * states.length)];
    const total = 1000;
    const current = randomState === 'ready' ? total : Math.floor(Math.random() * total);

    return {
        dataset_id,
        state: randomState,
        current,
        total,
        message: `Processing ${current} of ${total} samples`,
        error: null,
        updated_at: new Date().toISOString()
    };
}

// For testing: simulate progress updates
export function simulateProgress(dataset_id: string, onComplete?: () => void): () => void {
    const { progress, startProgress, updateProgress, setReady } = useDatasetProgress({ dataset_id });

    startProgress();

    let current = 0;
    const total = 100;

    const interval = setInterval(() => {
        current += Math.floor(Math.random() * 10) + 1;

        if (current >= total) {
            current = total;
            setReady();
            clearInterval(interval);
            onComplete?.();
        } else {
            updateProgress(current, total);
        }
    }, 500);

    // Return cleanup function
    return () => clearInterval(interval);
}
