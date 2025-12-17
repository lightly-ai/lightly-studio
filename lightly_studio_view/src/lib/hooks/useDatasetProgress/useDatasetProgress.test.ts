import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useDatasetProgress, simulateProgress } from './useDatasetProgress';
import { get } from 'svelte/store';
import type { DatasetProgress } from '$lib/components/DatasetProgress/types';
import * as progressApi from '$lib/services/progress/progressApi';
import * as websocket from '$lib/services/progress/websocket';

describe('useDatasetProgress Hook', () => {
    beforeEach(() => {
        vi.clearAllTimers();
        vi.clearAllMocks();
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.useRealTimers();
    });

    describe('initialization', () => {
        it('should initialize with null progress', () => {
            const { progress } = useDatasetProgress({
                dataset_id: 'test-dataset',
                mode: 'manual'
            });

            expect(get(progress)).toBeNull();
        });

        it('should initialize with isLoading false', () => {
            const { isLoading } = useDatasetProgress({
                dataset_id: 'test-dataset',
                mode: 'manual'
            });

            expect(get(isLoading)).toBe(false);
        });

        it('should initialize with no error', () => {
            const { error } = useDatasetProgress({
                dataset_id: 'test-dataset',
                mode: 'manual'
            });

            expect(get(error)).toBeNull();
        });
    });

    describe('manual mode', () => {
        it('should update progress manually', () => {
            const { progress, updateProgress } = useDatasetProgress({
                dataset_id: 'test-dataset',
                mode: 'manual'
            });

            updateProgress(50, 100, 'Processing...');

            const currentProgress = get(progress);
            expect(currentProgress).not.toBeNull();
            expect(currentProgress?.current).toBe(50);
            expect(currentProgress?.total).toBe(100);
            expect(currentProgress?.message).toBe('Processing...');
            expect(currentProgress?.state).toBe('indexing');
        });

        it('should transition to embedding state at 50% progress', () => {
            const { progress, updateProgress } = useDatasetProgress({
                dataset_id: 'test-dataset',
                mode: 'manual'
            });

            updateProgress(75, 100);

            const currentProgress = get(progress);
            expect(currentProgress?.state).toBe('embedding');
        });

        it('should transition to ready state at 100% progress', () => {
            const { progress, updateProgress, isLoading } = useDatasetProgress({
                dataset_id: 'test-dataset',
                mode: 'manual'
            });

            updateProgress(100, 100);

            const currentProgress = get(progress);
            expect(currentProgress?.state).toBe('ready');
            expect(get(isLoading)).toBe(false);
        });

        it('should set error state', () => {
            const { progress, error, setError, isLoading } = useDatasetProgress({
                dataset_id: 'test-dataset',
                mode: 'manual'
            });

            setError('Something went wrong');

            const currentProgress = get(progress);
            expect(currentProgress?.state).toBe('error');
            expect(currentProgress?.error).toBe('Something went wrong');
            expect(get(error)).toBe('Something went wrong');
            expect(get(isLoading)).toBe(false);
        });

        it('should set ready state', () => {
            const { progress, setReady, isLoading } = useDatasetProgress({
                dataset_id: 'test-dataset',
                mode: 'manual'
            });

            setReady();

            const currentProgress = get(progress);
            expect(currentProgress?.state).toBe('ready');
            expect(get(isLoading)).toBe(false);
        });
    });

    describe('polling mode', () => {
        it('should start polling when startProgress is called', async () => {
            const mockStartPolling = vi
                .spyOn(progressApi, 'startProgressPolling')
                .mockReturnValue(() => {});

            const { startProgress } = useDatasetProgress({
                dataset_id: 'test-dataset',
                mode: 'polling'
            });

            startProgress();

            expect(mockStartPolling).toHaveBeenCalled();
        });

        it('should stop polling when stopProgress is called', async () => {
            const mockCleanup = vi.fn();
            vi.spyOn(progressApi, 'startProgressPolling').mockReturnValue(mockCleanup);

            const { startProgress, stopProgress } = useDatasetProgress({
                dataset_id: 'test-dataset',
                mode: 'polling'
            });

            startProgress();
            stopProgress();

            expect(mockCleanup).toHaveBeenCalled();
        });

        it('should update progress on polling callback', async () => {
            const mockProgress: DatasetProgress = {
                dataset_id: 'test-dataset',
                state: 'indexing',
                current: 30,
                total: 100,
                message: 'Indexing...',
                error: null,
                updated_at: new Date().toISOString()
            };

            vi.spyOn(progressApi, 'startProgressPolling').mockImplementation(
                (_dataset_id, onUpdate) => {
                    // Immediately call onUpdate with mock data
                    setTimeout(() => onUpdate(mockProgress), 0);
                    return () => {};
                }
            );

            const { progress, startProgress } = useDatasetProgress({
                dataset_id: 'test-dataset',
                mode: 'polling'
            });

            startProgress();
            await vi.advanceTimersByTimeAsync(10);

            expect(get(progress)).toEqual(expect.objectContaining(mockProgress));
        });

        it('should set isLoading to false when progress is ready', async () => {
            const mockProgress: DatasetProgress = {
                dataset_id: 'test-dataset',
                state: 'ready',
                current: 100,
                total: 100,
                message: 'Complete',
                error: null,
                updated_at: new Date().toISOString()
            };

            vi.spyOn(progressApi, 'startProgressPolling').mockImplementation(
                (_dataset_id, onUpdate) => {
                    setTimeout(() => onUpdate(mockProgress), 0);
                    return () => {};
                }
            );

            const { isLoading, startProgress } = useDatasetProgress({
                dataset_id: 'test-dataset',
                mode: 'polling'
            });

            startProgress();
            await vi.advanceTimersByTimeAsync(10);

            expect(get(isLoading)).toBe(false);
        });

        it('should handle polling errors', async () => {
            const errorMessage = 'Failed to fetch progress after multiple attempts';

            vi.spyOn(progressApi, 'startProgressPolling').mockImplementation(
                (_dataset_id, _onUpdate, _interval, options) => {
                    setTimeout(() => options?.onError?.(new Error(errorMessage)), 0);
                    return () => {};
                }
            );

            const { error, startProgress } = useDatasetProgress({
                dataset_id: 'test-dataset',
                mode: 'polling'
            });

            startProgress();
            await vi.advanceTimersByTimeAsync(10);

            expect(get(error)).toBe(errorMessage);
        });

        it('should use custom polling interval', () => {
            const mockStartPolling = vi
                .spyOn(progressApi, 'startProgressPolling')
                .mockReturnValue(() => {});

            const customInterval = 5000;
            const { startProgress } = useDatasetProgress({
                dataset_id: 'test-dataset',
                mode: 'polling',
                pollingInterval: customInterval
            });

            startProgress();

            expect(mockStartPolling).toHaveBeenCalledWith(
                'test-dataset',
                expect.any(Function),
                customInterval,
                expect.any(Object)
            );
        });
    });

    describe('websocket mode', () => {
        it('should create WebSocket connection when startProgress is called', () => {
            const mockCreateWS = vi
                .spyOn(websocket, 'createProgressWebSocket')
                .mockReturnValue(() => {});

            const { startProgress } = useDatasetProgress({
                dataset_id: 'test-dataset',
                mode: 'websocket'
            });

            startProgress();

            expect(mockCreateWS).toHaveBeenCalledWith(
                expect.objectContaining({
                    dataset_id: 'test-dataset',
                    onUpdate: expect.any(Function),
                    onError: expect.any(Function)
                })
            );
        });

        it('should fall back to polling on WebSocket error', async () => {
            const mockStartPolling = vi
                .spyOn(progressApi, 'startProgressPolling')
                .mockReturnValue(() => {});

            vi.spyOn(websocket, 'createProgressWebSocket').mockImplementation((options) => {
                setTimeout(() => options.onError?.(new Error('WebSocket failed')), 0);
                return () => {};
            });

            const { startProgress } = useDatasetProgress({
                dataset_id: 'test-dataset',
                mode: 'websocket'
            });

            startProgress();
            await vi.advanceTimersByTimeAsync(10);

            expect(mockStartPolling).toHaveBeenCalled();
        });

        it('should update progress on WebSocket message', async () => {
            const mockProgress: DatasetProgress = {
                dataset_id: 'test-dataset',
                state: 'embedding',
                current: 75,
                total: 100,
                message: 'Embedding...',
                error: null,
                updated_at: new Date().toISOString()
            };

            vi.spyOn(websocket, 'createProgressWebSocket').mockImplementation((options) => {
                setTimeout(() => options.onUpdate(mockProgress), 0);
                return () => {};
            });

            const { progress, startProgress } = useDatasetProgress({
                dataset_id: 'test-dataset',
                mode: 'websocket'
            });

            startProgress();
            await vi.advanceTimersByTimeAsync(10);

            expect(get(progress)).toEqual(expect.objectContaining(mockProgress));
        });
    });

    describe('multiple datasets', () => {
        it('should maintain separate progress for different datasets', () => {
            const { progress: progress1, updateProgress: update1 } = useDatasetProgress({
                dataset_id: 'dataset-1',
                mode: 'manual'
            });

            const { progress: progress2, updateProgress: update2 } = useDatasetProgress({
                dataset_id: 'dataset-2',
                mode: 'manual'
            });

            update1(30, 100);
            update2(70, 100);

            expect(get(progress1)?.current).toBe(30);
            expect(get(progress2)?.current).toBe(70);
        });

        it('should share progress for same dataset across hooks', () => {
            const { updateProgress } = useDatasetProgress({
                dataset_id: 'shared-dataset',
                mode: 'manual'
            });

            const { progress: progress2 } = useDatasetProgress({
                dataset_id: 'shared-dataset',
                mode: 'manual'
            });

            updateProgress(50, 100);

            expect(get(progress2)?.current).toBe(50);
        });
    });

    describe('cleanup', () => {
        it('should stop progress on stopProgress call', () => {
            const mockCleanup = vi.fn();
            vi.spyOn(progressApi, 'startProgressPolling').mockReturnValue(mockCleanup);

            const { startProgress, stopProgress } = useDatasetProgress({
                dataset_id: 'test-dataset',
                mode: 'polling'
            });

            startProgress();
            stopProgress();

            expect(mockCleanup).toHaveBeenCalled();
        });

        it('should cleanup previous connection when starting new one', () => {
            const mockCleanup1 = vi.fn();
            const mockCleanup2 = vi.fn();

            vi.spyOn(progressApi, 'startProgressPolling')
                .mockReturnValueOnce(mockCleanup1)
                .mockReturnValueOnce(mockCleanup2);

            const { startProgress } = useDatasetProgress({
                dataset_id: 'test-dataset',
                mode: 'polling'
            });

            startProgress();
            startProgress(); // Start again

            expect(mockCleanup1).toHaveBeenCalled();
        });
    });

    describe('simulateProgress helper', () => {
        it('should simulate progress updates', async () => {
            const { progress } = useDatasetProgress({
                dataset_id: 'test-dataset',
                mode: 'manual'
            });

            const cleanup = simulateProgress('test-dataset');

            // Wait for some updates
            await vi.advanceTimersByTimeAsync(1000);

            const currentProgress = get(progress);
            expect(currentProgress).not.toBeNull();
            expect(currentProgress?.current).toBeGreaterThan(0);

            cleanup();
        });

        it('should call onComplete when simulation finishes', async () => {
            const onComplete = vi.fn();

            simulateProgress('test-dataset', onComplete);

            // Advance enough time for completion
            await vi.advanceTimersByTimeAsync(10000);

            expect(onComplete).toHaveBeenCalled();
        });

        it('should reach ready state on completion', async () => {
            const { progress } = useDatasetProgress({
                dataset_id: 'test-dataset',
                mode: 'manual'
            });

            simulateProgress('test-dataset');

            // Advance time until completion
            await vi.advanceTimersByTimeAsync(10000);

            const currentProgress = get(progress);
            expect(currentProgress?.state).toBe('ready');
            expect(currentProgress?.current).toBe(currentProgress?.total);
        });

        it('should stop simulation when cleanup is called', async () => {
            const { progress } = useDatasetProgress({
                dataset_id: 'test-dataset',
                mode: 'manual'
            });

            const cleanup = simulateProgress('test-dataset');

            await vi.advanceTimersByTimeAsync(500);
            const progressBefore = get(progress);

            cleanup();

            await vi.advanceTimersByTimeAsync(2000);
            const progressAfter = get(progress);

            // Progress should not change after cleanup
            expect(progressBefore?.current).toBe(progressAfter?.current);
        });
    });

    describe('edge cases', () => {
        it('should handle rapid start/stop calls', () => {
            const mockCleanup = vi.fn();
            vi.spyOn(progressApi, 'startProgressPolling').mockReturnValue(mockCleanup);

            const { startProgress, stopProgress } = useDatasetProgress({
                dataset_id: 'test-dataset',
                mode: 'polling'
            });

            startProgress();
            stopProgress();
            startProgress();
            stopProgress();

            expect(mockCleanup).toHaveBeenCalledTimes(2);
        });

        it('should handle progress with error field', async () => {
            const mockProgress: DatasetProgress = {
                dataset_id: 'test-dataset',
                state: 'indexing',
                current: 30,
                total: 100,
                message: 'Processing...',
                error: 'Warning message',
                updated_at: new Date().toISOString()
            };

            vi.spyOn(progressApi, 'startProgressPolling').mockImplementation(
                (_dataset_id, onUpdate) => {
                    setTimeout(() => onUpdate(mockProgress), 0);
                    return () => {};
                }
            );

            const { error, startProgress } = useDatasetProgress({
                dataset_id: 'test-dataset',
                mode: 'polling'
            });

            startProgress();
            await vi.advanceTimersByTimeAsync(10);

            expect(get(error)).toBe('Warning message');
        });

        it('should clear error when starting new progress', () => {
            const { error, setError, startProgress } = useDatasetProgress({
                dataset_id: 'test-dataset',
                mode: 'manual'
            });

            setError('Previous error');
            expect(get(error)).toBe('Previous error');

            startProgress();
            expect(get(error)).toBeNull();
        });
    });
});
