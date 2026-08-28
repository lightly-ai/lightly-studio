export interface McapTopic {
    topic: string;
    message_count: number;
    first_log_time_ns: string;
}

export interface McapSource {
    direct_url: string;
    size_bytes: number;
    version: string;
    topics: McapTopic[];
}

export type ProcessingPath = 'browser' | 'backend';

export interface ProcessingMetrics {
    /** UI request through usable frame, measured on the main thread. */
    totalMs: number;
    /** Indexed read and decode inside the worker or on the server. */
    processingMs: number;
    /** Summary-index parsing. Zero once the source index is cached. */
    indexMs: number;
    /** CDR parsing plus PointCloud2 to packed XYZI. */
    decodeMs: number;
    /** Source bytes read for this frame only, excluding index parsing. */
    bytesRead: number;
    /** Range requests (browser) or reader calls (backend) for this frame only. */
    requestCount: number;
    peakMemoryBytes?: number;
    indexCached: boolean;
}

export interface PointCloudFrame {
    points: Float32Array;
    pointCount: number;
    logTimeNs: string;
    metrics: ProcessingMetrics;
}

export interface WorkerRequest {
    requestId: number;
    url: string;
    sizeBytes: number;
    topic: string;
    timestampNs: string;
}

export interface WorkerSuccess {
    requestId: number;
    points: ArrayBuffer;
    pointCount: number;
    logTimeNs: string;
    metrics: ProcessingMetrics;
}

export interface WorkerFailure {
    requestId: number;
    error: string;
}

export type WorkerResponse = WorkerSuccess | WorkerFailure;

export interface MetricSummary {
    median: number;
    min: number;
    max: number;
}

export interface PathSummary {
    /** Number of warm runs the summary is computed from. */
    runs: number;
    totalMs: MetricSummary;
    processingMs: MetricSummary;
    decodeMs: MetricSummary;
    bytesRead: MetricSummary;
    requestCount: MetricSummary;
    peakMemoryBytes?: MetricSummary;
    /** Total time of the first run, which also parses the summary index. */
    coldTotalMs?: number;
}

export interface BenchmarkIteration {
    timestampNs: string;
    frames: Partial<Record<ProcessingPath, PointCloudFrame>>;
}

export interface BenchmarkResult {
    iterations: BenchmarkIteration[];
    summaries: Partial<Record<ProcessingPath, PathSummary>>;
    /** Iterations where both paths returned the same log time and point count. */
    matched: number;
    /** Iterations where both paths ran and could be compared. */
    compared: number;
}
