import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
    fetchDatasetProgress,
    startProgressPolling
} from './progressApi';
import type { DatasetProgress } from '$lib/components/DatasetProgress/types';
import { client } from '$lib/services/dataset';

// Mock the client module
vi.mock('$lib/services/dataset', () => ({
    client: {
        GET: vi.fn()
    }
}));

describe('progressApi', () => {
    beforeEach(() => {
        vi.clearAllTimers();
        vi.useFakeTimers();
        vi.clearAllMocks();
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    describe('fetchDatasetProgress', () => {
        it('should fetch progress with indexing in progress', async () => {
            const dataset_id = 'test-dataset';
            const mockGetFn = vi.mocked(client.GET);

            mockGetFn.mockResolvedValue({
                data: {
                    status_metadata: {
                        pending: 30,
                        processing: 20,
                        success: 50
                    },
                    status_embeddings: {
                        pending: 100,
                        processing: 0,
                        success: 0
                    }
                }
            } as any);

            const progress = await fetchDatasetProgress(dataset_id);

            expect(progress).toBeDefined();
            expect(progress?.dataset_id).toBe(dataset_id);
            expect(progress?.state).toBe('indexing');
            expect(progress?.current).toBe(50);
            expect(progress?.total).toBe(200);
        });

        it('should fetch progress with embedding in progress', async () => {
            const dataset_id = 'test-dataset';
            const mockGetFn = vi.mocked(client.GET);

            mockGetFn.mockResolvedValue({
                data: {
                    status_metadata: {
                        success: 100
                    },
                    status_embeddings: {
                        processing: 30,
                        success: 70
                    }
                }
            } as any);

            const progress = await fetchDatasetProgress(dataset_id);

            expect(progress?.state).toBe('embedding');
            expect(progress?.current).toBe(170);
            expect(progress?.total).toBe(200);
        });

        it('should show ready state when all complete', async () => {
            const dataset_id = 'test-dataset';
            const mockGetFn = vi.mocked(client.GET);

            mockGetFn.mockResolvedValue({
                data: {
                    status_metadata: {
                        success: 100
                    },
                    status_embeddings: {
                        success: 100
                    }
                }
            } as any);

            const progress = await fetchDatasetProgress(dataset_id);

            expect(progress?.state).toBe('ready');
            expect(progress?.current).toBe(200);
            expect(progress?.total).toBe(200);
        });

        it('should show error state when errors exist', async () => {
            const dataset_id = 'test-dataset';
            const mockGetFn = vi.mocked(client.GET);

            mockGetFn.mockResolvedValue({
                data: {
                    status_metadata: {
                        success: 80,
                        error: 20
                    },
                    status_embeddings: {
                        success: 100
                    }
                }
            } as any);

            const progress = await fetchDatasetProgress(dataset_id);

            expect(progress?.state).toBe('error');
            expect(progress?.error).toBeTruthy();
        });

        it('should handle API errors', async () => {
            const dataset_id = 'test-dataset';
            const mockGetFn = vi.mocked(client.GET);

            mockGetFn.mockResolvedValue({
                error: { message: 'API error' }
            } as any);

            await expect(fetchDatasetProgress(dataset_id)).rejects.toThrow();
        });
    });

    describe('startProgressPolling', () => {
        it('should call onUpdate callback with progress', async () => {
            const dataset_id = 'test-dataset';
            const onUpdate = vi.fn();
            const mockGetFn = vi.mocked(client.GET);

            mockGetFn.mockResolvedValue({
                data: {
                    status_metadata: { processing: 50, success: 50 },
                    status_embeddings: { pending: 100 }
                }
            } as any);

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
            const mockGetFn = vi.mocked(client.GET);

            mockGetFn.mockResolvedValue({
                data: {
                    status_metadata: { processing: 50, success: 50 },
                    status_embeddings: { pending: 100 }
                }
            } as any);

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
            const mockGetFn = vi.mocked(client.GET);

            mockGetFn.mockResolvedValue({
                data: {
                    status_metadata: { processing: 50, success: 50 },
                    status_embeddings: { pending: 100 }
                }
            } as any);

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
            const mockGetFn = vi.mocked(client.GET);

            mockGetFn.mockResolvedValue({
                data: {
                    status_metadata: { success: 100 },
                    status_embeddings: { success: 100 }
                }
            } as any);

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
            const mockGetFn = vi.mocked(client.GET);

            mockGetFn.mockResolvedValue({
                data: {
                    status_metadata: { success: 80, error: 20 },
                    status_embeddings: { success: 100 }
                }
            } as any);

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

});
