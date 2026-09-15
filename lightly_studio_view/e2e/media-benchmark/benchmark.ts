import { execFile } from 'node:child_process';
import { createHash } from 'node:crypto';
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';
import type { Browser, BrowserContext, Page, Request, Response } from '@playwright/test';

export const REPETITIONS = readRepetitions();
export const CACHE_STATE = process.env.LIG_8835_CACHE_STATE === 'warm' ? 'warm' : 'cold';

export type ImageCondition = 'proxy-original' | 'direct-original' | 'proxy-thumbnail';
export type VideoCondition = 'proxy' | 'direct';

export interface NetworkEntry {
    url: string;
    delivery: 'studio' | 'storage';
    status: number | null;
    durationMs: number | null;
    responseBytes: number | null;
    failure: string | null;
}

export interface BackendSampleSummary {
    pid: number;
    samples: number;
    peakCpuPercent: number | null;
    peakRssMb: number | null;
}

interface BackendSample {
    cpuPercent: number;
    rssMb: number;
}

export class BackendSampler {
    private readonly pid = readBackendPid();
    private readonly samples: BackendSample[] = [];
    private timer: ReturnType<typeof setInterval> | undefined;

    start(): void {
        if (this.pid === null) return;
        this.sample();
        this.timer = setInterval(() => this.sample(), 100);
    }

    async stop(): Promise<BackendSampleSummary | null> {
        if (this.timer) clearInterval(this.timer);
        if (this.pid === null) return null;
        await new Promise((resolve) => setTimeout(resolve, 150));
        return {
            pid: this.pid,
            samples: this.samples.length,
            peakCpuPercent: maximum(this.samples.map((sample) => sample.cpuPercent)),
            peakRssMb: maximum(this.samples.map((sample) => sample.rssMb))
        };
    }

    private sample(): void {
        if (this.pid === null) return;
        execFile('ps', ['-o', '%cpu=,rss=', '-p', String(this.pid)], (error, stdout) => {
            if (error) return;
            const [cpu, rss] = stdout.trim().split(/\s+/).map(Number);
            if (Number.isFinite(cpu) && Number.isFinite(rss)) {
                this.samples.push({ cpuPercent: cpu, rssMb: rss / 1024 });
            }
        });
    }
}

export function conditionOrder<T>(conditions: readonly T[], repetition: number): T[] {
    const offset = repetition % conditions.length;
    return [...conditions.slice(offset), ...conditions.slice(0, offset)];
}

export async function createBenchmarkContext({
    browser,
    existingContext
}: {
    browser: Browser;
    existingContext?: BrowserContext;
}): Promise<BrowserContext> {
    if (existingContext) return existingContext;
    return browser.newContext({ viewport: { width: 1600, height: 1200 } });
}

export function rewriteImageUrl(url: string, condition: ImageCondition): string {
    const rewritten = new URL(url);
    if (condition !== 'proxy-thumbnail') {
        rewritten.searchParams.delete('quality');
        rewritten.searchParams.delete('max_width');
        rewritten.searchParams.delete('max_height');
    }
    if (condition === 'direct-original') rewritten.searchParams.delete('mode');
    else rewritten.searchParams.set('mode', 'proxy');
    return rewritten.toString();
}

export function rewriteVideoUrl(url: string, condition: VideoCondition): string {
    const rewritten = new URL(url);
    if (condition === 'proxy') rewritten.searchParams.set('mode', 'proxy');
    else rewritten.searchParams.delete('mode');
    return rewritten.toString();
}

export function collectMediaNetwork(page: Page): {
    entries: NetworkEntry[];
    settle: () => Promise<void>;
} {
    const entries: NetworkEntry[] = [];
    const pending = new Set<Promise<void>>();
    page.on('response', (response) => trackResponse(response));
    page.on('requestfailed', (request) => trackFailure(request));

    function trackResponse(response: Response): void {
        if (!isMediaRequest(response.request())) return;
        const promise = recordNetworkEntry(response.request(), response, null).then((entry) =>
            entries.push(entry)
        );
        pending.add(promise);
        void promise.finally(() => pending.delete(promise));
    }

    function trackFailure(request: Request): void {
        if (!isMediaRequest(request)) return;
        const failure = request.failure()?.errorText ?? 'unknown';
        entries.push(createNetworkEntry(request, null, {}, failure));
    }

    return {
        entries,
        settle: async () => {
            await Promise.all([...pending]);
        }
    };
}

export function summarizeNetwork(entries: NetworkEntry[]): {
    studioMediaBodyBytes: number;
    storageMediaBodyBytes: number;
    studioRequests: number;
    storageRequests: number;
    studioBodyResponses: number;
    storageBodyResponses: number;
    failures: number;
} {
    const isBodyResponse = (entry: NetworkEntry) => [200, 206].includes(entry.status ?? 0);
    const bodyBytes = (delivery: NetworkEntry['delivery']) =>
        entries
            .filter((entry) => entry.delivery === delivery && isBodyResponse(entry))
            .reduce((total, entry) => total + (entry.responseBytes ?? 0), 0);
    return {
        studioMediaBodyBytes: bodyBytes('studio'),
        storageMediaBodyBytes: bodyBytes('storage'),
        studioRequests: entries.filter((entry) => entry.delivery === 'studio').length,
        storageRequests: entries.filter((entry) => entry.delivery === 'storage').length,
        studioBodyResponses: entries.filter(
            (entry) => entry.delivery === 'studio' && isBodyResponse(entry)
        ).length,
        storageBodyResponses: entries.filter(
            (entry) => entry.delivery === 'storage' && isBodyResponse(entry)
        ).length,
        failures: entries.filter((entry) => entry.failure !== null).length
    };
}

export function summarize(values: number[]): { median: number; min: number; max: number } {
    if (values.length === 0) throw new Error('Cannot summarize an empty measurement set.');
    const sorted = [...values].sort((left, right) => left - right);
    const middle = Math.floor(sorted.length / 2);
    const median =
        sorted.length % 2 === 0 ? (sorted[middle - 1] + sorted[middle]) / 2 : sorted[middle];
    return { median, min: sorted[0], max: sorted.at(-1)! };
}

export async function measureLightweightApi(page: Page): Promise<number> {
    const start = performance.now();
    const response = await page.request.get('/api/features');
    if (!response.ok())
        throw new Error(`The concurrent /api/features request returned ${response.status()}.`);
    return performance.now() - start;
}

export function writeArtifact(filename: string, results: unknown, browserVersion: string): string {
    const outputDirectory = process.env.LIG_8835_RESULTS_DIR ?? 'test-results/lig-8835';
    fs.mkdirSync(outputDirectory, { recursive: true });
    const outputPath = path.join(outputDirectory, filename);
    const artifact = {
        schemaVersion: 1,
        generatedAt: new Date().toISOString(),
        repetitions: REPETITIONS,
        cacheState: CACHE_STATE,
        viewport: { width: 1600, height: 1200 },
        browserVersion,
        runtime: { node: process.version, platform: os.platform(), release: os.release() },
        runMetadata: readRunMetadata(),
        results
    };
    fs.writeFileSync(outputPath, JSON.stringify(artifact, null, 2));
    return outputPath;
}

function readBackendPid(): number | null {
    const value = process.env.LIG_8835_BACKEND_PID;
    if (!value) return null;
    if (!/^\d+$/.test(value)) throw new Error('LIG_8835_BACKEND_PID must be a positive integer.');
    return Number(value);
}

function readRepetitions(): number {
    const repetitions = Number(process.env.LIG_8835_REPETITIONS ?? 10);
    if (!Number.isInteger(repetitions) || repetitions < 1) {
        throw new Error('LIG_8835_REPETITIONS must be a positive integer.');
    }
    return repetitions;
}

function readRunMetadata(): Record<string, string | null> {
    return {
        commit: process.env.LIG_8835_COMMIT ?? null,
        dataset: process.env.LIG_8835_DATASET ?? null,
        objectSet: process.env.LIG_8835_OBJECT_SET ?? null,
        backendRegion: process.env.LIG_8835_BACKEND_REGION ?? null,
        bucketRegion: process.env.LIG_8835_BUCKET_REGION ?? null,
        browserRegion: process.env.LIG_8835_BROWSER_REGION ?? null,
        network: process.env.LIG_8835_NETWORK ?? 'unthrottled'
    };
}

function maximum(values: number[]): number | null {
    return values.length > 0 ? Math.max(...values) : null;
}

function isMediaRequest(request: Request): boolean {
    let current: Request | null = request;
    while (current) {
        if (/\/(images\/sample|videos\/media)\//.test(new URL(current.url()).pathname)) return true;
        current = current.redirectedFrom();
    }
    return false;
}

async function recordNetworkEntry(
    request: Request,
    response: Response,
    failure: string | null
): Promise<NetworkEntry> {
    const headers = await response.allHeaders();
    return createNetworkEntry(request, response, headers, failure);
}

function createNetworkEntry(
    request: Request,
    response: Response | null,
    headers: Record<string, string>,
    failure: string | null
): NetworkEntry {
    const contentLength = Number(headers['content-length']);
    const timing = request.timing();
    return {
        url: redactUrl(request.url()),
        delivery: /\/(images\/sample|videos\/media)\//.test(new URL(request.url()).pathname)
            ? 'studio'
            : 'storage',
        status: response?.status() ?? null,
        durationMs: timing.responseEnd >= 0 ? timing.responseEnd : null,
        responseBytes: Number.isFinite(contentLength) ? contentLength : null,
        failure
    };
}

function redactUrl(value: string): string {
    const url = new URL(value);
    const identifier = createHash('sha256')
        .update(`${url.origin}${url.pathname}`)
        .digest('hex')
        .slice(0, 12);
    const studioMediaPath = url.pathname.match(/\/(images\/sample|videos\/media)\//)?.[1];
    return studioMediaPath
        ? `studio:/${studioMediaPath}/<redacted-${identifier}>`
        : `storage://<redacted>/<redacted-${identifier}>`;
}
