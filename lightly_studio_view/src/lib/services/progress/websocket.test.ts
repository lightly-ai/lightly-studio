import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ProgressWebSocket, createProgressWebSocket } from './websocket';
import type { DatasetProgress } from '$lib/components/DatasetProgress/types';

// Mock WebSocket
class MockWebSocket {
    static CONNECTING = 0;
    static OPEN = 1;
    static CLOSING = 2;
    static CLOSED = 3;

    readyState = MockWebSocket.CONNECTING;
    onopen: ((event: Event) => void) | null = null;
    onmessage: ((event: MessageEvent) => void) | null = null;
    onerror: ((event: Event) => void) | null = null;
    onclose: ((event: CloseEvent) => void) | null = null;

    constructor(public url: string) {
        // Simulate connection opening
        setTimeout(() => {
            this.readyState = MockWebSocket.OPEN;
            this.onopen?.(new Event('open'));
        }, 10);
    }

    send(data: string) {
        if (this.readyState !== MockWebSocket.OPEN) {
            throw new Error('WebSocket is not open');
        }
    }

    close() {
        this.readyState = MockWebSocket.CLOSED;
        this.onclose?.(new CloseEvent('close'));
    }

    // Helper method to simulate receiving a message
    simulateMessage(data: unknown) {
        if (this.readyState === MockWebSocket.OPEN) {
            this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }));
        }
    }

    // Helper method to simulate an error
    simulateError() {
        this.onerror?.(new Event('error'));
    }
}

describe('ProgressWebSocket', () => {
    beforeEach(() => {
        vi.clearAllTimers();
        vi.useFakeTimers();
        global.WebSocket = MockWebSocket as any;
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.useRealTimers();
    });

    describe('constructor and connect', () => {
        it('should create WebSocket with correct URL', () => {
            const dataset_id = 'test-dataset';
            const onUpdate = vi.fn();

            const ws = new ProgressWebSocket({ dataset_id, onUpdate });
            ws.connect();

            expect(ws).toBeDefined();
        });

        it('should call onConnect when connection opens', async () => {
            const dataset_id = 'test-dataset';
            const onConnect = vi.fn();
            const onUpdate = vi.fn();

            const ws = new ProgressWebSocket({
                dataset_id,
                onUpdate,
                onConnect
            });

            ws.connect();
            await vi.advanceTimersByTimeAsync(20);

            expect(onConnect).toHaveBeenCalled();
        });

        it('should send subscribe message on connect', async () => {
            const dataset_id = 'test-dataset';
            const onUpdate = vi.fn();

            const ws = new ProgressWebSocket({ dataset_id, onUpdate });
            const sendSpy = vi.spyOn(MockWebSocket.prototype, 'send');

            ws.connect();
            await vi.advanceTimersByTimeAsync(20);

            expect(sendSpy).toHaveBeenCalledWith(
                JSON.stringify({
                    type: 'subscribe',
                    dataset_id
                })
            );
        });
    });

    describe('message handling', () => {
        it('should call onUpdate with progress data', async () => {
            const dataset_id = 'test-dataset';
            const onUpdate = vi.fn();

            const ws = new ProgressWebSocket({ dataset_id, onUpdate });
            ws.connect();
            await vi.advanceTimersByTimeAsync(20);

            const progressData: DatasetProgress = {
                dataset_id,
                state: 'indexing',
                current: 50,
                total: 100,
                message: 'Processing...',
                error: null,
                updated_at: new Date().toISOString()
            };

            // Simulate receiving message
            const mockWs = (ws as any).ws as MockWebSocket;
            mockWs.simulateMessage({
                type: 'progress_update',
                payload: progressData
            });

            expect(onUpdate).toHaveBeenCalledWith(progressData);
        });

        it('should call onError on error message', async () => {
            const dataset_id = 'test-dataset';
            const onUpdate = vi.fn();
            const onError = vi.fn();

            const ws = new ProgressWebSocket({
                dataset_id,
                onUpdate,
                onError
            });

            ws.connect();
            await vi.advanceTimersByTimeAsync(20);

            const mockWs = (ws as any).ws as MockWebSocket;
            mockWs.simulateMessage({
                type: 'error',
                message: 'Test error'
            });

            expect(onError).toHaveBeenCalledWith(expect.any(Error));
        });

        it('should handle invalid JSON gracefully', async () => {
            const dataset_id = 'test-dataset';
            const onUpdate = vi.fn();
            const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

            const ws = new ProgressWebSocket({ dataset_id, onUpdate });
            ws.connect();
            await vi.advanceTimersByTimeAsync(20);

            const mockWs = (ws as any).ws as MockWebSocket;
            mockWs.onmessage?.(new MessageEvent('message', { data: 'invalid json' }));

            expect(consoleSpy).toHaveBeenCalled();
            consoleSpy.mockRestore();
        });
    });

    describe('disconnect', () => {
        it('should send unsubscribe message on disconnect', async () => {
            const dataset_id = 'test-dataset';
            const onUpdate = vi.fn();

            const ws = new ProgressWebSocket({ dataset_id, onUpdate });
            ws.connect();
            await vi.advanceTimersByTimeAsync(20);

            const sendSpy = vi.spyOn(MockWebSocket.prototype, 'send');
            ws.disconnect();

            expect(sendSpy).toHaveBeenCalledWith(
                JSON.stringify({
                    type: 'unsubscribe',
                    dataset_id
                })
            );
        });

        it('should call onDisconnect when connection closes', async () => {
            const dataset_id = 'test-dataset';
            const onUpdate = vi.fn();
            const onDisconnect = vi.fn();

            const ws = new ProgressWebSocket({
                dataset_id,
                onUpdate,
                onDisconnect
            });

            ws.connect();
            await vi.advanceTimersByTimeAsync(20);

            ws.disconnect();

            expect(onDisconnect).toHaveBeenCalled();
        });

        it('should not attempt reconnect after intentional disconnect', async () => {
            const dataset_id = 'test-dataset';
            const onUpdate = vi.fn();
            const onConnect = vi.fn();

            const ws = new ProgressWebSocket({
                dataset_id,
                onUpdate,
                onConnect
            });

            ws.connect();
            await vi.advanceTimersByTimeAsync(20);
            expect(onConnect).toHaveBeenCalledTimes(1);

            ws.disconnect();
            await vi.advanceTimersByTimeAsync(10000); // Wait for potential reconnect

            expect(onConnect).toHaveBeenCalledTimes(1); // Should not reconnect
        });
    });

    describe('reconnection', () => {
        it('should attempt reconnection on unexpected disconnect', async () => {
            const dataset_id = 'test-dataset';
            const onUpdate = vi.fn();
            const onConnect = vi.fn();

            const ws = new ProgressWebSocket({
                dataset_id,
                onUpdate,
                onConnect,
                reconnectInterval: 1000
            });

            ws.connect();
            await vi.advanceTimersByTimeAsync(20);
            expect(onConnect).toHaveBeenCalledTimes(1);

            // Simulate unexpected disconnect
            const mockWs = (ws as any).ws as MockWebSocket;
            mockWs.close();

            // Wait for reconnect
            await vi.advanceTimersByTimeAsync(1100);
            expect(onConnect).toHaveBeenCalledTimes(2);
        });

        it('should stop reconnecting after max attempts', async () => {
            const dataset_id = 'test-dataset';
            const onUpdate = vi.fn();
            const onError = vi.fn();
            const maxAttempts = 3;

            const ws = new ProgressWebSocket({
                dataset_id,
                onUpdate,
                onError,
                reconnectInterval: 1000,
                maxReconnectAttempts: maxAttempts
            });

            ws.connect();

            // Simulate repeated failures
            for (let i = 0; i <= maxAttempts; i++) {
                await vi.advanceTimersByTimeAsync(20);
                const mockWs = (ws as any).ws as MockWebSocket;
                mockWs.close();
                await vi.advanceTimersByTimeAsync(1000);
            }

            expect(onError).toHaveBeenCalledWith(
                expect.objectContaining({
                    message: 'Failed to reconnect to WebSocket'
                })
            );
        });

        it('should reset reconnect attempts on successful connection', async () => {
            const dataset_id = 'test-dataset';
            const onUpdate = vi.fn();
            const onConnect = vi.fn();

            const ws = new ProgressWebSocket({
                dataset_id,
                onUpdate,
                onConnect,
                reconnectInterval: 1000
            });

            ws.connect();
            await vi.advanceTimersByTimeAsync(20);
            expect(onConnect).toHaveBeenCalledTimes(1);

            // First disconnect and reconnect
            const mockWs1 = (ws as any).ws as MockWebSocket;
            mockWs1.close();
            await vi.advanceTimersByTimeAsync(1100);
            expect(onConnect).toHaveBeenCalledTimes(2);

            // Second disconnect and reconnect (should work because attempts were reset)
            const mockWs2 = (ws as any).ws as MockWebSocket;
            mockWs2.close();
            await vi.advanceTimersByTimeAsync(1100);
            expect(onConnect).toHaveBeenCalledTimes(3);
        });
    });

    describe('error handling', () => {
        it('should call onError on WebSocket error', async () => {
            const dataset_id = 'test-dataset';
            const onUpdate = vi.fn();
            const onError = vi.fn();

            const ws = new ProgressWebSocket({
                dataset_id,
                onUpdate,
                onError
            });

            ws.connect();
            await vi.advanceTimersByTimeAsync(20);

            const mockWs = (ws as any).ws as MockWebSocket;
            mockWs.simulateError();

            expect(onError).toHaveBeenCalledWith(
                expect.objectContaining({
                    message: 'WebSocket connection error'
                })
            );
        });
    });

    describe('isConnected', () => {
        it('should return true when connected', async () => {
            const dataset_id = 'test-dataset';
            const onUpdate = vi.fn();

            const ws = new ProgressWebSocket({ dataset_id, onUpdate });
            expect(ws.isConnected()).toBe(false);

            ws.connect();
            await vi.advanceTimersByTimeAsync(20);

            expect(ws.isConnected()).toBe(true);
        });

        it('should return false when disconnected', async () => {
            const dataset_id = 'test-dataset';
            const onUpdate = vi.fn();

            const ws = new ProgressWebSocket({ dataset_id, onUpdate });
            ws.connect();
            await vi.advanceTimersByTimeAsync(20);

            expect(ws.isConnected()).toBe(true);

            ws.disconnect();
            expect(ws.isConnected()).toBe(false);
        });
    });

    describe('createProgressWebSocket helper', () => {
        it('should create and connect WebSocket', async () => {
            const dataset_id = 'test-dataset';
            const onUpdate = vi.fn();
            const onConnect = vi.fn();

            const cleanup = createProgressWebSocket({
                dataset_id,
                onUpdate,
                onConnect
            });

            await vi.advanceTimersByTimeAsync(20);
            expect(onConnect).toHaveBeenCalled();

            cleanup();
        });

        it('should return cleanup function that disconnects', async () => {
            const dataset_id = 'test-dataset';
            const onUpdate = vi.fn();
            const onDisconnect = vi.fn();

            const cleanup = createProgressWebSocket({
                dataset_id,
                onUpdate,
                onDisconnect
            });

            await vi.advanceTimersByTimeAsync(20);

            cleanup();
            expect(onDisconnect).toHaveBeenCalled();
        });
    });
});
