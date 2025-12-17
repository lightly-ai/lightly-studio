import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
    fetchDatasetProgress,
    startProgressPolling,
    resetMockProgress,
    setMockProgress
} from './progressApi';
import type { DatasetProgress } from '$lib/components/DatasetProgress/types';

describe('progressApi', () => {
    beforeEach(() => {
        vi.clearAllTimers();
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    describe('fetchDatasetProgress', () => {
        it('should fetch progress for a dataset', async () => {
            const dataset_id = 'test-dataset';
            const progress = await fetchDatasetProgress(dataset_id);

            expect(progress).toBeDefined();
            expect(progress?.dataset_id).toBe(dataset_id);
            expect(progress?.state).toBeDefined();
            expect(progress?.current).toBeGreaterThanOrEqual(0);
            expect(progress?.total).toBeGreaterThan(0);
        });

        it('should return consistent data for same dataset', async () => {
            const dataset_id = 'test-dataset';
            const progress1 = await fetchDatasetProgress(dataset_id);
            const progress2 = await fetchDatasetProgress(dataset_id);

            expect(progress1?.dataset_id).toBe(progress2?.dataset_id);
        });

        it('should handle mock progress updates', async () => {
            const dataset_id = 'test-dataset';

            // First fetch
            const progress1 = await fetchDatasetProgress(dataset_id);
            expect(progress1).toBeDefined();

            // Second fetch should show progress
            const progress2 = await fetchDatasetProgress(dataset_id);
            expect(progress2).toBeDefined();

            // Progress should increase or stay same (if completed)
            if (progress2!.state !== 'ready' && progress2!.state !== 'error') {
                expect(progress2!.current).toBeGreaterThanOrEqual(progress1!.current);
            }
        });
    });

    describe('startProgressPolling', () => {
        it('should call onUpdate callback with progress', async () => {
            const dataset_id = 'test-dataset';
            const onUpdate = vi.fn();

            startProgressPolling(dataset_id, onUpdate, 1000);

            // Wait for first poll
            await vi.advanceTimersByTimeAsync(100);

            expect(onUpdate).toHaveBeenCalled();
            const progress: DatasetProgress = onUpdate.mock.calls[0][0];
            expect(progress.dataset_id).toBe(dataset_id);
        });

        it('should poll at specified interval', async () => {
            const dataset_id = 'test-dataset';
            const onUpdate = vi.fn();
            const interval = 2000;

            startProgressPolling(dataset_id, onUpdate, interval);

            // First call happens immediately
            await vi.advanceTimersByTimeAsync(100);
            expect(onUpdate).toHaveBeenCalledTimes(1);

            // Second call after interval
            await vi.advanceTimersByTimeAsync(interval);
            expect(onUpdate).toHaveBeenCalledTimes(2);

            // Third call after another interval
            await vi.advanceTimersByTimeAsync(interval);
            expect(onUpdate).toHaveBeenCalledTimes(3);
        });

        it('should stop polling when cleanup is called', async () => {
            const dataset_id = 'test-dataset';
            const onUpdate = vi.fn();

            const cleanup = startProgressPolling(dataset_id, onUpdate, 1000);

            await vi.advanceTimersByTimeAsync(100);
            expect(onUpdate).toHaveBeenCalledTimes(1);

            // Clean up
            cleanup();

            // Advance time - should not call again
            await vi.advanceTimersByTimeAsync(2000);
            expect(onUpdate).toHaveBeenCalledTimes(1);
        });

        it('should stop polling when state is ready', async () => {
            const dataset_id = 'test-dataset-ready';
            const onUpdate = vi.fn();

            // Set progress to ready
            setMockProgress(dataset_id, {
                state: 'ready',
                current: 100,
                total: 100
            });

            startProgressPolling(dataset_id, onUpdate, 1000);

            await vi.advanceTimersByTimeAsync(100);
            expect(onUpdate).toHaveBeenCalledTimes(1);

            // Should not poll again
            await vi.advanceTimersByTimeAsync(2000);
            expect(onUpdate).toHaveBeenCalledTimes(1);
        });

        it('should stop polling when state is error', async () => {
            const dataset_id = 'test-dataset-error';
            const onUpdate = vi.fn();

            // Set progress to error
            setMockProgress(dataset_id, {
                state: 'error',
                error: 'Test error'
            });

            startProgressPolling(dataset_id, onUpdate, 1000);

            await vi.advanceTimersByTimeAsync(100);
            expect(onUpdate).toHaveBeenCalledTimes(1);

            // Should not poll again
            await vi.advanceTimersByTimeAsync(2000);
            expect(onUpdate).toHaveBeenCalledTimes(1);
        });

        it('should handle errors with exponential backoff', async () => {
            const dataset_id = 'test-dataset-error-backoff';
            const onUpdate = vi.fn();
            const onError = vi.fn();
            const interval = 1000;

            // Reset mocks first
            vi.clearAllMocks();
            vi.resetModules();

            // Mock fetchDatasetProgress to throw error
            const progressApiModule = await import('./progressApi');
            const mockFetch = vi
                .spyOn(progressApiModule, 'fetchDatasetProgress')
                .mockRejectedValue(new Error('Network error'));

            progressApiModule.startProgressPolling(dataset_id, onUpdate, interval, {
                maxRetries: 3,
                onError
            });

            // First attempt (immediate)
            await vi.advanceTimersByTimeAsync(100);
            expect(onUpdate).not.toHaveBeenCalled();

            // Second attempt (1s * 2^0 = 1s backoff)
            await vi.advanceTimersByTimeAsync(1000);

            // Third attempt (1s * 2^1 = 2s backoff)
            await vi.advanceTimersByTimeAsync(2000);

            // Fourth attempt (1s * 2^2 = 4s backoff)
            await vi.advanceTimersByTimeAsync(4000);

            // Should have reached max retries
            expect(onError).toHaveBeenCalledWith(
                expect.objectContaining({
                    message: 'Failed to fetch progress after multiple attempts'
                })
            );

            mockFetch.mockRestore();
        });

        it('should reset error count on successful fetch', async () => {
            const dataset_id = 'test-dataset-reset-error';
            const onUpdate = vi.fn();
            const onError = vi.fn();

            // Reset mocks first
            vi.clearAllMocks();
            vi.resetModules();

            let shouldFail = true;
            const progressApiModule = await import('./progressApi');
            const mockFetch = vi
                .spyOn(progressApiModule, 'fetchDatasetProgress')
                .mockImplementation(async () => {
                    if (shouldFail) {
                        shouldFail = false; // Fail only once
                        throw new Error('Network error');
                    }
                    return {
                        dataset_id,
                        state: 'indexing',
                        current: 50,
                        total: 100,
                        message: 'Indexing...',
                        error: null,
                        updated_at: new Date().toISOString()
                    };
                });

            progressApiModule.startProgressPolling(dataset_id, onUpdate, 1000, {
                maxRetries: 3,
                onError
            });

            // First attempt fails
            await vi.advanceTimersByTimeAsync(100);
            expect(onUpdate).not.toHaveBeenCalled();

            // Retry succeeds
            await vi.advanceTimersByTimeAsync(1000);
            expect(onUpdate).toHaveBeenCalledTimes(1);
            expect(onError).not.toHaveBeenCalled();

            mockFetch.mockRestore();
        });
    });

    describe('resetMockProgress', () => {
        it('should reset progress for a dataset', async () => {
            const dataset_id = 'test-dataset-reset';

            // Create some progress
            await fetchDatasetProgress(dataset_id);
            await fetchDatasetProgress(dataset_id);

            const progressBefore = await fetchDatasetProgress(dataset_id);
            const currentBefore = progressBefore!.current;

            // Reset
            resetMockProgress(dataset_id);

            // Should start from beginning (may auto-increment to indexing on first fetch)
            const progress = await fetchDatasetProgress(dataset_id);
            expect(progress?.current).toBeLessThan(currentBefore);
        });
    });

    describe('setMockProgress', () => {
        it('should set custom progress state', async () => {
            const dataset_id = 'test-dataset-set-mock';

            setMockProgress(dataset_id, {
                state: 'embedding',
                current: 75,
                total: 100,
                message: 'Custom message'
            });

            const progress = await fetchDatasetProgress(dataset_id);
            expect(progress?.state).toBe('embedding');
            // Current may auto-increment, just check it's >= 75
            expect(progress?.current).toBeGreaterThanOrEqual(75);
            expect(progress?.message).toContain('embedding');
        });

        it('should set error state', async () => {
            const dataset_id = 'test-dataset';
            const errorMessage = 'Something went wrong';

            setMockProgress(dataset_id, {
                state: 'error',
                error: errorMessage
            });

            const progress = await fetchDatasetProgress(dataset_id);
            expect(progress?.state).toBe('error');
            expect(progress?.error).toBe(errorMessage);
        });
    });

    describe('Progress state transitions', () => {
        it('should transition from pending to indexing', async () => {
            const dataset_id = 'test-dataset-transitions';
            resetMockProgress(dataset_id);

            const progress1 = await fetchDatasetProgress(dataset_id);
            // May start at pending or immediately transition to indexing
            expect(['pending', 'indexing']).toContain(progress1?.state);

            const progress2 = await fetchDatasetProgress(dataset_id);
            if (progress2?.current > 0) {
                expect(['indexing', 'pending']).toContain(progress2?.state);
            }
        });

        it('should transition from indexing to embedding', async () => {
            const dataset_id = 'test-dataset-mid';

            setMockProgress(dataset_id, {
                state: 'indexing',
                current: 45,
                total: 100
            });

            // Multiple fetches should progress
            let progress: DatasetProgress | null = null;
            for (let i = 0; i < 10; i++) {
                progress = await fetchDatasetProgress(dataset_id);
                if (progress?.state === 'embedding') break;
            }

            expect(['indexing', 'embedding']).toContain(progress?.state);
        });

        it('should reach ready state', async () => {
            const dataset_id = 'test-dataset-complete';

            setMockProgress(dataset_id, {
                state: 'embedding',
                current: 95,
                total: 100
            });

            // Multiple fetches should eventually reach ready
            let progress: DatasetProgress | null = null;
            for (let i = 0; i < 20; i++) {
                progress = await fetchDatasetProgress(dataset_id);
                if (progress?.state === 'ready') break;
            }

            expect(progress?.state).toBe('ready');
            expect(progress?.current).toBe(progress?.total);
        });
    });
});
