/// <reference lib="webworker" />
import { openMcap } from './mcapReader';
import { ProviderError } from './providerError';
import type { WorkerCommand, WorkerRequest, WorkerResult } from './workerProtocol';

let session: Awaited<ReturnType<typeof openMcap>> | undefined;
const controller = new AbortController();

function bytesRead(): number {
    return session?.readable.bytesRead ?? 0;
}

async function runCommand(command: WorkerCommand, result: WorkerResult): Promise<void> {
    if (command.kind === 'open') {
        session = await openMcap(command.source, controller.signal);
        result.metadata = session.metadata;
        return;
    }
    if (!session) throw new ProviderError('source', 'Open a recording before requesting frames.');
    if (command.kind === 'frame') {
        result.frame = await session.loadFrame(command.locator, command.pointBudget);
        return;
    }
    result.range = await session.listFrames(
        command.channelId,
        command.startTimeNs,
        command.endTimeNs,
        command.limit
    );
}

/**
 * Unknown failures are reported as corrupt input rather than leaking internals.
 *
 * The cause still travels in `detail`, which diagnostics and logs read: a generic message
 * with no way to find out what actually broke is not actionable for anyone.
 */
function toWorkerError(error: unknown): NonNullable<WorkerResult['error']> {
    if (error instanceof ProviderError) {
        return {
            code: error.code,
            message: error.message,
            ...(error.detail === undefined ? {} : { detail: error.detail })
        };
    }
    return {
        code: 'corrupt',
        message:
            'The MCAP recording could not be read or decoded. Check its index, schema, and payload.',
        detail: error instanceof Error ? `${error.name}: ${error.message}` : String(error)
    };
}

self.onmessage = async ({ data }: MessageEvent<WorkerRequest>) => {
    const started = performance.now();
    const beforeBytes = bytesRead();
    const { command, requestId } = data;
    const result: WorkerResult = { requestId };
    try {
        self.postMessage({ requestId, phase: command.kind === 'open' ? 'indexing' : 'decoding' });
        await runCommand(command, result);
        result.durationMs = performance.now() - started;
        result.bytesRead = bytesRead() - beforeBytes;
        const transfer = result.frame ? [result.frame.positions.buffer as ArrayBuffer] : [];
        self.postMessage(result, { transfer });
    } catch (error) {
        result.error = toWorkerError(error);
        result.durationMs = performance.now() - started;
        self.postMessage(result);
    }
};
