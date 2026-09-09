import type { PointCloudFrameTransfer } from '../domain';
import type { openMcap } from './mcapReader';
import type { FrameLocator, McapSource } from './source';
import type { ProviderError } from './providerError';

type Session = Awaited<ReturnType<typeof openMcap>>;
export type WorkerCommand =
    | { kind: 'open'; source: McapSource }
    | { kind: 'frame'; locator: FrameLocator; pointBudget: number }
    | { kind: 'range'; channelId: number; startTimeNs: string; endTimeNs: string; limit: number };

export interface WorkerRequest {
    requestId: number;
    command: WorkerCommand;
}

export interface WorkerResult {
    requestId: number;
    phase?: 'indexing' | 'decoding';
    metadata?: Session['metadata'];
    frame?: PointCloudFrameTransfer;
    range?: Awaited<ReturnType<Session['listFrames']>>;
    durationMs?: number;
    bytesRead?: number;
    error?: { code: ProviderError['code']; message: string; detail?: string };
}
