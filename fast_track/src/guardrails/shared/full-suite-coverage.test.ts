import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('node:fs', () => ({
    existsSync: vi.fn(),
    readFileSync: vi.fn()
}));

import { existsSync, readFileSync } from 'node:fs';
import { createCoverageGuardrail } from './full-suite-coverage';
import type { CoverageConfig, LineCoverage } from './full-suite-coverage';
import type { ChangedFile, GuardrailContext } from '../context/types';

const mockExistsSync = vi.mocked(existsSync);
const mockReadFileSync = vi.mocked(readFileSync);

const COVERAGE_ENV = 'TEST_COVERAGE_JSON';
const PASSED_ENV = 'TEST_TESTS_PASSED';
const REPORT_PATH = '/tmp/coverage.json';

// Adds lines 1–3 of the new file.
const PATCH = '@@ -0,0 +1,3 @@\n+line 1\n+line 2\n+line 3\n';

const FILE: ChangedFile = {
    path: 'pkg/src/model.py',
    status: 'modified',
    additions: 3,
    deletions: 0,
    patch: PATCH
};

function range(from: number, to: number): number[] {
    return Array.from({ length: to - from + 1 }, (_, i) => from + i);
}

function coverage(covered: number[], missing: number[], path = FILE.path): LineCoverage {
    return new Map([
        [path, { executable: new Set([...covered, ...missing]), covered: new Set(covered) }]
    ]);
}

function makeConfig(overrides: Partial<CoverageConfig> = {}): CoverageConfig {
    return {
        name: 'test/coverage',
        coverageJsonEnvVar: COVERAGE_ENV,
        testsPassedEnvVar: PASSED_ENV,
        filterFiles: (files: ChangedFile[]): ChangedFile[] => files,
        parseReport: (): LineCoverage => coverage([1, 2, 3], []),
        ...overrides
    };
}

function makeCtx(files: ChangedFile[]): GuardrailContext {
    return { baseRef: 'origin/main', changedFiles: async () => files };
}

function setReportAvailable(): void {
    process.env[COVERAGE_ENV] = REPORT_PATH;
    mockExistsSync.mockReturnValue(true);
    mockReadFileSync.mockReturnValue('{}');
}

function clearEnv(): void {
    delete process.env[COVERAGE_ENV];
    delete process.env[PASSED_ENV];
}

// Cleared on both sides so an ambient value in the environment cannot leak into
// the cases that need these unset.
beforeEach(() => {
    vi.resetAllMocks();
    clearEnv();
});

afterEach(clearEnv);

describe('createCoverageGuardrail', () => {
    it('is required and runs locally', () => {
        const g = createCoverageGuardrail(makeConfig());
        expect(g.name).toBe('test/coverage');
        expect(g.required).toBe(true);
        expect(g.needsPrContext).toBe(false);
    });

    it('passes without reading the report when no file is in scope', async () => {
        const g = createCoverageGuardrail(makeConfig({ filterFiles: () => [] }));
        const result = await g.run(makeCtx([FILE]));
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('0 file(s) checked');
        expect(mockExistsSync).not.toHaveBeenCalled();
    });

    it('skips deleted files', async () => {
        const g = createCoverageGuardrail(makeConfig());
        const result = await g.run(makeCtx([{ ...FILE, status: 'deleted' }]));
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('0 file(s) checked');
    });

    it('skips files without a patch', async () => {
        const g = createCoverageGuardrail(makeConfig());
        const noPatch: ChangedFile = { ...FILE, patch: undefined };
        const result = await g.run(makeCtx([noPatch]));
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('0 file(s) checked');
    });

    it('skips files whose patch adds no lines', async () => {
        const deletionOnly: ChangedFile = {
            ...FILE,
            additions: 0,
            deletions: 3,
            patch: '@@ -1,3 +1,0 @@\n-line 1\n-line 2\n-line 3\n'
        };
        const g = createCoverageGuardrail(makeConfig());
        const result = await g.run(makeCtx([deletionOnly]));
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('0 file(s) checked');
    });

    it('passes with a loud summary when the env var is unset (local run)', async () => {
        const g = createCoverageGuardrail(makeConfig());
        const result = await g.run(makeCtx([FILE]));
        expect(result.status).toBe('pass');
        expect(result.summary).toContain(`coverage skipped: ${COVERAGE_ENV} not set`);
    });

    it('fails when the test suite was red', async () => {
        setReportAvailable();
        process.env[PASSED_ENV] = 'false';
        const g = createCoverageGuardrail(makeConfig());
        const result = await g.run(makeCtx([FILE]));
        expect(result.status).toBe('fail');
        expect(result.summary).toContain('test suite failed');
        expect(mockReadFileSync).not.toHaveBeenCalled();
    });

    it('fails when the report is missing', async () => {
        process.env[COVERAGE_ENV] = REPORT_PATH;
        mockExistsSync.mockReturnValue(false);
        const g = createCoverageGuardrail(makeConfig());
        const result = await g.run(makeCtx([FILE]));
        expect(result.status).toBe('fail');
        expect(result.summary).toContain('coverage report missing');
        expect(result.summary).toContain(REPORT_PATH);
    });

    it('reads the report from the path in the env var', async () => {
        setReportAvailable();
        const g = createCoverageGuardrail(makeConfig());
        await g.run(makeCtx([FILE]));
        expect(mockReadFileSync).toHaveBeenCalledWith(REPORT_PATH, 'utf-8');
    });

    it('passes when every added line is covered', async () => {
        setReportAvailable();
        const g = createCoverageGuardrail(makeConfig());
        const result = await g.run(makeCtx([FILE]));
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('[PASS]');
        expect(result.summary).toContain(FILE.path);
    });

    it('passes at exactly the 90% threshold', async () => {
        setReportAvailable();
        const g = createCoverageGuardrail(
            makeConfig({ parseReport: () => coverage([1, 2, 3, 4, 5, 6, 7, 8, 9], [10]) })
        );
        const result = await g.run(
            makeCtx([{ ...FILE, patch: '@@ -0,0 +1,10 @@\n' + '+x\n'.repeat(10) }])
        );
        expect(result.status).toBe('pass');
    });

    it('fails below the 90% threshold', async () => {
        setReportAvailable();
        const g = createCoverageGuardrail(makeConfig({ parseReport: () => coverage([1, 2], [3]) }));
        const result = await g.run(makeCtx([FILE]));
        expect(result.status).toBe('fail');
        expect(result.summary).toContain('66.7%');
        expect(result.summary).toContain('90%');
        expect(result.summary).toContain(FILE.path);
    });

    // coverage.py records only statements, so comments, blank lines, continuation
    // lines and closing brackets are absent from the report entirely. A diff of
    // nothing but those has no coverable code to judge.
    it('passes when no added line is an executable statement', async () => {
        setReportAvailable();
        const g = createCoverageGuardrail(makeConfig({ parseReport: () => coverage([10], [11]) }));
        const result = await g.run(makeCtx([FILE]));
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('no executable added lines');
    });

    // The two cases below pin the ratio to the added lines. Each is built so that
    // judging the whole file instead would flip the verdict, which the empty-
    // intersection case above cannot detect on its own.
    it('excludes covered lines outside the diff, which would mask uncovered added lines', async () => {
        setReportAvailable();
        // Added lines 1–2 are executable and uncovered; lines 10–29 are covered.
        // Added-line ratio 0/2 = 0%; whole-file would be 20/22 = 90.9% and pass.
        const g = createCoverageGuardrail(
            makeConfig({ parseReport: () => coverage(range(10, 29), [1, 2]) })
        );
        const result = await g.run(makeCtx([FILE]));
        expect(result.status).toBe('fail');
        expect(result.summary).toContain('0.0%');
    });

    it('excludes uncovered lines outside the diff, which would sink covered added lines', async () => {
        setReportAvailable();
        // Added lines 1–3 are all covered; lines 10–29 are executable and not.
        // Added-line ratio 3/3 = 100%; whole-file would be 3/23 = 13% and fail.
        const g = createCoverageGuardrail(
            makeConfig({ parseReport: () => coverage([1, 2, 3], range(10, 29)) })
        );
        const result = await g.run(makeCtx([FILE]));
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('100.0%');
    });

    it('fails a file absent from the report', async () => {
        setReportAvailable();
        const g = createCoverageGuardrail(makeConfig({ parseReport: () => new Map() }));
        const result = await g.run(makeCtx([FILE]));
        expect(result.status).toBe('fail');
        expect(result.summary).toContain('not found in coverage report');
        expect(result.summary).toContain(FILE.path);
    });

    it('judges each file on its own ratio rather than pooling them', async () => {
        setReportAvailable();
        const other: ChangedFile = { ...FILE, path: 'pkg/src/service.py' };
        const g = createCoverageGuardrail(
            makeConfig({
                parseReport: () =>
                    new Map([
                        [
                            FILE.path,
                            { executable: new Set([1, 2, 3]), covered: new Set([1, 2, 3]) }
                        ],
                        [other.path, { executable: new Set([1, 2, 3]), covered: new Set() }]
                    ])
            })
        );
        const result = await g.run(makeCtx([FILE, other]));
        expect(result.status).toBe('fail');
        expect(result.summary).toContain(`[PASS] ${FILE.path}`);
        expect(result.summary).toContain(`[FAIL] ${other.path}`);
    });
});
