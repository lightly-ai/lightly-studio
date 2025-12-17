import type { DatasetProgress } from '$lib/components/DatasetProgress/types';
import { PUBLIC_LIGHTLY_STUDIO_API_URL } from '$env/static/public';

export interface WebSocketProgressOptions {
    dataset_id: string;
    onUpdate: (progress: DatasetProgress) => void;
    onError?: (error: Error) => void;
    onConnect?: () => void;
    onDisconnect?: () => void;
    reconnectInterval?: number;
    maxReconnectAttempts?: number;
}

export class ProgressWebSocket {
    private ws: WebSocket | null = null;
    private options: WebSocketProgressOptions;
    private reconnectAttempts = 0;
    private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
    private isIntentionallyClosed = false;

    constructor(options: WebSocketProgressOptions) {
        this.options = {
            reconnectInterval: 5000,
            maxReconnectAttempts: 5,
            ...options
        };
    }

    connect(): void {
        this.isIntentionallyClosed = false;

        try {
            // Convert HTTP URL to WebSocket URL
            const wsUrl = this.getWebSocketUrl();
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log(`WebSocket connected for dataset ${this.options.dataset_id}`);
                this.reconnectAttempts = 0;
                this.options.onConnect?.();

                // Subscribe to progress updates for this dataset
                this.send({
                    type: 'subscribe',
                    dataset_id: this.options.dataset_id
                });
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);

                    if (data.type === 'progress_update') {
                        const progress: DatasetProgress = data.payload;
                        this.options.onUpdate(progress);
                    } else if (data.type === 'error') {
                        this.options.onError?.(new Error(data.message));
                    }
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.options.onError?.(new Error('WebSocket connection error'));
            };

            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.options.onDisconnect?.();

                if (!this.isIntentionallyClosed) {
                    this.attemptReconnect();
                }
            };
        } catch (error) {
            console.error('Error creating WebSocket:', error);
            this.options.onError?.(error as Error);
        }
    }

    private getWebSocketUrl(): string {
        // Convert HTTP(S) URL to WS(S) URL
        const apiUrl = PUBLIC_LIGHTLY_STUDIO_API_URL || 'http://localhost:8000';
        const wsUrl = apiUrl.replace(/^http/, 'ws');
        return `${wsUrl}/api/datasets/${this.options.dataset_id}/progress/ws`;
    }

    private send(data: unknown): void {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    }

    private attemptReconnect(): void {
        if (
            this.reconnectAttempts >= (this.options.maxReconnectAttempts || 5) ||
            this.isIntentionallyClosed
        ) {
            console.log('Max reconnect attempts reached');
            this.options.onError?.(new Error('Failed to reconnect to WebSocket'));
            return;
        }

        this.reconnectAttempts++;
        console.log(
            `Attempting to reconnect (${this.reconnectAttempts}/${this.options.maxReconnectAttempts})...`
        );

        this.reconnectTimeout = setTimeout(() => {
            this.connect();
        }, this.options.reconnectInterval);
    }

    disconnect(): void {
        this.isIntentionallyClosed = true;

        if (this.reconnectTimeout) {
            clearTimeout(this.reconnectTimeout);
            this.reconnectTimeout = null;
        }

        if (this.ws) {
            // Unsubscribe before closing
            this.send({
                type: 'unsubscribe',
                dataset_id: this.options.dataset_id
            });

            this.ws.close();
            this.ws = null;
        }
    }

    isConnected(): boolean {
        return this.ws?.readyState === WebSocket.OPEN;
    }
}

/**
 * Create a WebSocket connection for progress updates
 * @returns Cleanup function to disconnect
 */
export function createProgressWebSocket(
    options: WebSocketProgressOptions
): () => void {
    const ws = new ProgressWebSocket(options);
    ws.connect();

    return () => ws.disconnect();
}
