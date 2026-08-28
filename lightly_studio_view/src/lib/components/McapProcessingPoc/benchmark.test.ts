import { describe, expect, it, vi } from 'vitest';
import { collect, isSameFrame, median, runBenchmark, summarize, toMarkdown } from './benchmark';
import type { McapSource, PointCloudFrame, ProcessingPath } from './types';

describe('median', () => {
    it('averages the two middle values of an even sample', () => {
        expect(median([4, 1, 3, 2])).toBe(2.5);
    });

    it('returns NaN for an empty sample', () => {
        expect(median([])).toBeNaN();
    });
});

describe('summarize', () => {
    it('reports the cold run separately from the warm medians', () => {
        const frames = [
            frame({ totalMs: 90, indexCached: false }),
            frame({ totalMs: 10 }),
            frame()
        ];

        const summary = summarize(frames);

        expect(summary?.runs).toBe(2);
        expect(summary?.coldTotalMs).toBe(90);
        expect(summary?.totalMs.median).toBe(7.5);
        expect(summary?.totalMs.max).toBe(10);
    });

    it('falls back to the cold run when no warm run exists', () => {
        const summary = summarize([frame({ totalMs: 90, indexCached: false })]);

        expect(summary?.runs).toBe(1);
        expect(summary?.totalMs.median).toBe(90);
    });

    it('omits peak memory when no run reported it', () => {
        expect(summarize([frame()])?.peakMemoryBytes).toBeUndefined();
    });

    it('returns undefined without frames', () => {
        expect(summarize([])).toBeUndefined();
    });
});

describe('isSameFrame', () => {
    it('compares log time and point count across both paths', () => {
        const iteration = {
            timestampNs: '1',
            frames: { browser: frame(), backend: frame() }
        };

        expect(isSameFrame(iteration)).toBe(true);
        expect(isSameFrame({ ...iteration, frames: { browser: frame() } })).toBe(false);
        expect(
            isSameFrame({
                timestampNs: '1',
                frames: { browser: frame(), backend: frame({ pointCount: 7 }) }
            })
        ).toBe(false);
    });
});

describe('collect', () => {
    it('counts only iterations where both paths ran', () => {
        const result = collect(
            [
                { timestampNs: '1', frames: { browser: frame(), backend: frame() } },
                { timestampNs: '2', frames: { browser: frame() } }
            ],
            ['browser', 'backend']
        );

        expect(result.compared).toBe(1);
        expect(result.matched).toBe(1);
        expect(result.summaries.browser?.runs).toBe(2);
        expect(result.summaries.backend?.runs).toBe(1);
    });
});

describe('runBenchmark', () => {
    it('advances the timestamp and alternates which path runs first', async () => {
        const calls: string[] = [];
        const load = vi.fn(async (path: ProcessingPath, timestampNs: string) => {
            calls.push(`${path}@${timestampNs}`);
            return frame();
        });

        const result = await runBenchmark({
            runs: 2,
            paths: ['browser', 'backend'],
            startTimestampNs: '100',
            stepNs: 50n,
            load
        });

        expect(calls).toEqual(['browser@100', 'backend@100', 'backend@150', 'browser@150']);
        expect(result.iterations.map((item) => item.timestampNs)).toEqual(['100', '150']);
        expect(result.matched).toBe(2);
    });
});

describe('toMarkdown', () => {
    it('renders one row per path with the cold run called out', () => {
        const result = collect(
            [
                {
                    timestampNs: '1',
                    frames: {
                        browser: frame({ totalMs: 90, indexCached: false }),
                        backend: frame({ totalMs: 80, indexCached: false })
                    }
                },
                { timestampNs: '2', frames: { browser: frame({ totalMs: 8 }), backend: frame() } }
            ],
            ['browser', 'backend']
        );

        const markdown = toMarkdown(result, { source: source(), topic: '/lidar/points' });

        expect(markdown).toContain('Frames compared: 2/2 identical');
        expect(markdown).toContain('| browser (1 warm runs) | 90 |');
        expect(markdown).toContain('| backend (1 warm runs) | 80 |');
    });
});

function frame(overrides: Partial<PointCloudFrame['metrics']> & { pointCount?: number } = {}) {
    const { pointCount = 3, ...metrics } = overrides;
    return {
        points: new Float32Array(pointCount * 4),
        pointCount,
        logTimeNs: '42',
        metrics: {
            totalMs: 5,
            processingMs: 4,
            indexMs: 0,
            decodeMs: 1,
            bytesRead: 2048,
            requestCount: 2,
            indexCached: true,
            ...metrics
        }
    } satisfies PointCloudFrame;
}

function source(): McapSource {
    return {
        direct_url: 'http://localhost/api/mcap-poc/source/content',
        size_bytes: 2_000_000,
        version: 'v1',
        topics: []
    };
}
