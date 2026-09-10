import { ProviderError } from './providerError';
import type { WorkerCommand, WorkerRequest, WorkerResult } from './workerProtocol';

interface WorkerPort {
    onmessage: ((event: MessageEvent<WorkerResult>) => void) | null;
    onerror: ((event: ErrorEvent) => void) | null;
    postMessage(message: WorkerRequest): void;
    terminate(): void;
}

/** One in-flight operation. Aborting terminates synchronous decoding as well as fetches. */
export class WorkerClient {
    #worker: WorkerPort | undefined;
    #requestId = 0;
    #pending = false;

    constructor(
        private readonly createWorker: () => WorkerPort = () =>
            new Worker(new URL('./mcap.worker.ts', import.meta.url), { type: 'module' })
    ) {}

    async request(command: WorkerCommand, signal: AbortSignal, onPhase: (phase: string) => void) {
        signal.throwIfAborted();
        if (this.#pending) throw new Error('A worker request is already running.');
        this.#worker ??= this.createWorker();
        const worker = this.#worker;
        const requestId = ++this.#requestId;
        this.#pending = true;
        return new Promise<WorkerResult>((resolve, reject) => {
            const cleanup = () => {
                signal.removeEventListener('abort', abort);
                worker.onmessage = null;
                worker.onerror = null;
                this.#pending = false;
            };
            const abort = () => {
                cleanup();
                this.dispose();
                reject(signal.reason);
            };
            signal.addEventListener('abort', abort, { once: true });
            worker.onmessage = ({ data }) => {
                if (data.requestId !== requestId) return;
                if (data.phase) {
                    onPhase(data.phase);
                    return;
                }
                cleanup();
                if (data.error)
                    reject(
                        new ProviderError(data.error.code, data.error.message, data.error.detail)
                    );
                else resolve(data);
            };
            worker.onerror = () => {
                cleanup();
                this.dispose();
                reject(
                    new ProviderError(
                        'source',
                        'The MCAP worker failed. Reload the recording and retry.'
                    )
                );
            };
            try {
                worker.postMessage({ requestId, command });
            } catch (error) {
                cleanup();
                this.dispose();
                reject(error);
            }
        });
    }

    dispose(): void {
        this.#worker?.terminate();
        this.#worker = undefined;
    }
}
