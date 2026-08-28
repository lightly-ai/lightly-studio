import type {
    BenchmarkIteration,
    BenchmarkResult,
    McapSource,
    MetricSummary,
    PathSummary,
    PointCloudFrame,
    ProcessingPath
} from './types';

export interface BenchmarkOptions {
    runs: number;
    paths: ProcessingPath[];
    startTimestampNs: string;
    /** Nanoseconds to advance between runs, so repeated runs do not re-read one hot frame. */
    stepNs: bigint;
    load: (path: ProcessingPath, timestampNs: string) => Promise<PointCloudFrame>;
    onIteration?: (iteration: BenchmarkIteration) => void;
}

/**
 * Runs both processing paths over the same frames, alternating which path goes first so that
 * neither systematically benefits from the operating system's page cache.
 */
export async function runBenchmark(options: BenchmarkOptions): Promise<BenchmarkResult> {
    const iterations: BenchmarkIteration[] = [];
    let timestampNs = BigInt(options.startTimestampNs);
    for (let run = 0; run < options.runs; run += 1) {
        const iteration: BenchmarkIteration = { timestampNs: timestampNs.toString(), frames: {} };
        for (const path of orderedPaths(options.paths, run)) {
            iteration.frames[path] = await options.load(path, iteration.timestampNs);
        }
        iterations.push(iteration);
        options.onIteration?.(iteration);
        timestampNs += options.stepNs;
    }
    return collect(iterations, options.paths);
}

export function collect(
    iterations: BenchmarkIteration[],
    paths: ProcessingPath[]
): BenchmarkResult {
    const summaries: BenchmarkResult['summaries'] = {};
    for (const path of paths) {
        const summary = summarize(framesFor(iterations, path));
        if (summary) summaries[path] = summary;
    }
    const comparable = iterations.filter((item) => item.frames.browser && item.frames.backend);
    return {
        iterations,
        summaries,
        compared: comparable.length,
        matched: comparable.filter(isSameFrame).length
    };
}

/**
 * Summarises the warm runs of one path. The first run also parses the summary index, so it is
 * reported separately instead of skewing the medians.
 */
export function summarize(frames: PointCloudFrame[]): PathSummary | undefined {
    if (frames.length === 0) return undefined;
    const warm = frames.filter((frame) => frame.metrics.indexCached);
    const sample = warm.length > 0 ? warm : frames;
    const of = (pick: (frame: PointCloudFrame) => number): MetricSummary =>
        summarizeMetric(sample.map(pick));
    const peak = sample
        .map((frame) => frame.metrics.peakMemoryBytes)
        .filter((value): value is number => typeof value === 'number' && value > 0);
    return {
        runs: sample.length,
        totalMs: of((frame) => frame.metrics.totalMs),
        processingMs: of((frame) => frame.metrics.processingMs),
        decodeMs: of((frame) => frame.metrics.decodeMs),
        bytesRead: of((frame) => frame.metrics.bytesRead),
        requestCount: of((frame) => frame.metrics.requestCount),
        peakMemoryBytes: peak.length > 0 ? summarizeMetric(peak) : undefined,
        coldTotalMs: frames.find((frame) => !frame.metrics.indexCached)?.metrics.totalMs
    };
}

export function summarizeMetric(values: number[]): MetricSummary {
    return { median: median(values), min: Math.min(...values), max: Math.max(...values) };
}

export function median(values: number[]): number {
    if (values.length === 0) return Number.NaN;
    const sorted = [...values].sort((first, second) => first - second);
    const middle = Math.floor(sorted.length / 2);
    return sorted.length % 2 === 0 ? (sorted[middle - 1] + sorted[middle]) / 2 : sorted[middle];
}

export function isSameFrame(iteration: BenchmarkIteration): boolean {
    const { browser, backend } = iteration.frames;
    if (!browser || !backend) return false;
    return browser.logTimeNs === backend.logTimeNs && browser.pointCount === backend.pointCount;
}

/** Renders the result as a markdown table that can be pasted into the issue. */
export function toMarkdown(
    result: BenchmarkResult,
    context: { source: McapSource; topic: string }
): string {
    const header = [
        `Source: \`${context.source.direct_url}\` (${mb(context.source.size_bytes)} MB)`,
        `Topic: \`${context.topic}\``,
        `Frames compared: ${result.matched}/${result.compared} identical`,
        '',
        '| Path | Cold total ms | Total ms | Processing ms | Decode ms | Source KB | Reads | Peak MB |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |'
    ];
    const rows = (['browser', 'backend'] as ProcessingPath[])
        .map((path) => markdownRow(path, result.summaries[path]))
        .filter((row): row is string => row !== undefined);
    return [...header, ...rows].join('\n');
}

function markdownRow(path: ProcessingPath, summary?: PathSummary): string | undefined {
    if (!summary) return undefined;
    const cells = [
        `${path} (${summary.runs} warm runs)`,
        summary.coldTotalMs === undefined ? '—' : round(summary.coldTotalMs),
        range(summary.totalMs),
        range(summary.processingMs),
        range(summary.decodeMs),
        range(summary.bytesRead, 1 / 1024),
        range(summary.requestCount),
        summary.peakMemoryBytes ? range(summary.peakMemoryBytes, 1e-6) : '—'
    ];
    return `| ${cells.join(' | ')} |`;
}

function range(summary: MetricSummary, scale = 1): string {
    return `${round(summary.median * scale)} (${round(summary.min * scale)}–${round(summary.max * scale)})`;
}

function round(value: number): string {
    return value.toLocaleString('en-US', { maximumFractionDigits: 1 });
}

function mb(bytes: number): string {
    return round(bytes / 1e6);
}

function framesFor(iterations: BenchmarkIteration[], path: ProcessingPath): PointCloudFrame[] {
    return iterations
        .map((iteration) => iteration.frames[path])
        .filter((frame): frame is PointCloudFrame => frame !== undefined);
}

function orderedPaths(paths: ProcessingPath[], run: number): ProcessingPath[] {
    return run % 2 === 0 ? paths : [...paths].reverse();
}
