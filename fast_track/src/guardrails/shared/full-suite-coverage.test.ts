import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('node:fs', () => ({
    existsSync: vi.fn(),
    readFileSync: vi.fn()
}));

import { existsSync, readFileSync } from 'node:fs';
import { createCoverageGuardrail } from './full-suite-coverage';
import type { CoverageConfig, LineCoverage } from './full-suite-coverage';
import type { ChangedFile, Guardrail, GuardrailOutcome } from '../context/types';

const mockExistsSync = vi.mocked(existsSync);
const mockReadFileSync = vi.mocked(readFileSync);

const COVERAGE_ENV = 'TEST_COVERAGE_JSON';
const PASSED_ENV = 'TEST_TESTS_PASSED';
const REPORT_PATH = '/tmp/coverage.json';

const MODEL = 'pkg/src/model.py';
const SERVICE = 'pkg/src/service.py';

/** A changed file whose diff adds `count` new lines, numbered 1..count. */
function fileAddingLines(count: number, path = MODEL): ChangedFile {
    const added = Array.from({ length: count }, (_, index) => `+line ${index + 1}\n`).join('');
    return {
        path,
        status: 'modified',
        additions: count,
        deletions: 0,
        patch: `@@ -0,0 +1,${count} @@\n${added}`
    };
}

/** A changed file whose diff only removes lines, adding none. */
function fileRemovingLines(count: number, path = MODEL): ChangedFile {
    const removed = Array.from({ length: count }, (_, index) => `-line ${index + 1}\n`).join('');
    return {
        path,
        status: 'modified',
        additions: 0,
        deletions: count,
        patch: `@@ -1,${count} +1,0 @@\n${removed}`
    };
}

interface FileCoverage {
    path?: string;
    /** Executable lines the suite ran. */
    coveredLines: number[];
    /** Executable lines the suite never ran. */
    uncoveredLines: number[];
}

/**
 * A parsed report. Any line absent from both lists is not executable, exactly as
 * a real report omits comments and blank lines.
 */
function reportFor(...files: FileCoverage[]): LineCoverage {
    return new Map(
        files.map(({ path = MODEL, coveredLines, uncoveredLines }) => [
            path,
            {
                executable: new Set([...coveredLines, ...uncoveredLines]),
                covered: new Set(coveredLines)
            }
        ])
    );
}

function reportListingNoFiles(): LineCoverage {
    return new Map();
}

function lineRange(from: number, to: number): number[] {
    return Array.from({ length: to - from + 1 }, (_, index) => from + index);
}

function coverageGuardrail(overrides: Partial<CoverageConfig> = {}): Guardrail {
    return createCoverageGuardrail({
        name: 'test/coverage',
        coverageJsonEnvVar: COVERAGE_ENV,
        testsPassedEnvVar: PASSED_ENV,
        filterFiles: (files: ChangedFile[]): ChangedFile[] => files,
        parseReport: (): LineCoverage => reportFor({ coveredLines: [1, 2, 3], uncoveredLines: [] }),
        ...overrides
    });
}

function runOn(guardrail: Guardrail, ...files: ChangedFile[]): Promise<GuardrailOutcome> {
    return guardrail.run({ baseRef: 'origin/main', changedFiles: async () => files });
}

function givenTheReportExists(): void {
    process.env[COVERAGE_ENV] = REPORT_PATH;
    mockExistsSync.mockReturnValue(true);
    mockReadFileSync.mockReturnValue('{}');
}

function givenTheReportPathIsSetButNothingIsThere(): void {
    process.env[COVERAGE_ENV] = REPORT_PATH;
    mockExistsSync.mockReturnValue(false);
}

function givenTheTestSuiteWasRed(): void {
    process.env[PASSED_ENV] = 'false';
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
        const guardrail = coverageGuardrail();
        expect(guardrail.name).toBe('test/coverage');
        expect(guardrail.required).toBe(true);
        expect(guardrail.needsPrContext).toBe(false);
    });

    it('passes without reading the report when no file is in scope', async () => {
        givenTheReportExists();
        const guardrail = coverageGuardrail({ filterFiles: () => [] });

        const result = await runOn(guardrail, fileAddingLines(3));

        expect(result.status).toBe('pass');
        expect(result.summary).toContain('0 file(s) checked');
        expect(mockExistsSync).not.toHaveBeenCalled();
    });

    it('skips deleted files', async () => {
        const deleted: ChangedFile = { ...fileAddingLines(3), status: 'deleted' };

        const result = await runOn(coverageGuardrail(), deleted);

        expect(result.status).toBe('pass');
        expect(result.summary).toContain('0 file(s) checked');
    });

    it('skips files without a patch', async () => {
        const noPatch: ChangedFile = { ...fileAddingLines(3), patch: undefined };

        const result = await runOn(coverageGuardrail(), noPatch);

        expect(result.status).toBe('pass');
        expect(result.summary).toContain('0 file(s) checked');
    });

    it('skips files whose patch adds no lines', async () => {
        const result = await runOn(coverageGuardrail(), fileRemovingLines(3));

        expect(result.status).toBe('pass');
        expect(result.summary).toContain('0 file(s) checked');
    });

    it('passes with a loud summary when the env var is unset (local run)', async () => {
        const result = await runOn(coverageGuardrail(), fileAddingLines(3));

        expect(result.status).toBe('pass');
        expect(result.summary).toContain(`coverage skipped: ${COVERAGE_ENV} not set`);
    });

    it('fails when the test suite was red', async () => {
        givenTheReportExists();
        givenTheTestSuiteWasRed();

        const result = await runOn(coverageGuardrail(), fileAddingLines(3));

        expect(result.status).toBe('fail');
        expect(result.summary).toContain('test suite failed');
        expect(mockReadFileSync).not.toHaveBeenCalled();
    });

    it('fails when the report is missing', async () => {
        givenTheReportPathIsSetButNothingIsThere();

        const result = await runOn(coverageGuardrail(), fileAddingLines(3));

        expect(result.status).toBe('fail');
        expect(result.summary).toContain('coverage report missing');
        expect(result.summary).toContain(REPORT_PATH);
    });

    it('reads the report from the path in the env var', async () => {
        givenTheReportExists();

        await runOn(coverageGuardrail(), fileAddingLines(3));

        expect(mockReadFileSync).toHaveBeenCalledWith(REPORT_PATH, 'utf-8');
    });

    it('passes when every added line is covered', async () => {
        givenTheReportExists();
        const guardrail = coverageGuardrail({
            parseReport: () => reportFor({ coveredLines: [1, 2, 3], uncoveredLines: [] })
        });

        const result = await runOn(guardrail, fileAddingLines(3));

        expect(result.status).toBe('pass');
        expect(result.summary).toContain(`[PASS] ${MODEL}`);
    });

    it('passes at exactly the 90% threshold: 9 of 10 added lines covered', async () => {
        givenTheReportExists();
        const guardrail = coverageGuardrail({
            parseReport: () => reportFor({ coveredLines: lineRange(1, 9), uncoveredLines: [10] })
        });

        const result = await runOn(guardrail, fileAddingLines(10));

        expect(result.status).toBe('pass');
        expect(result.summary).toContain('90.0%');
    });

    it('fails below the 90% threshold: 2 of 3 added lines covered', async () => {
        givenTheReportExists();
        const guardrail = coverageGuardrail({
            parseReport: () => reportFor({ coveredLines: [1, 2], uncoveredLines: [3] })
        });

        const result = await runOn(guardrail, fileAddingLines(3));

        expect(result.status).toBe('fail');
        expect(result.summary).toContain('66.7%');
        expect(result.summary).toContain('required 90%');
        expect(result.summary).toContain(MODEL);
    });

    // A report lists only statements, so comments, blank lines and closing brackets
    // are absent from it; a diff of nothing but those has no coverable code to judge.
    it('passes when no added line is an executable statement', async () => {
        givenTheReportExists();
        // The file is in the report, but none of its added lines 1–3 is.
        const guardrail = coverageGuardrail({
            parseReport: () => reportFor({ coveredLines: [10], uncoveredLines: [11] })
        });

        const result = await runOn(guardrail, fileAddingLines(3));

        expect(result.status).toBe('pass');
        expect(result.summary).toContain('no executable added lines');
    });

    // The two cases below pin the ratio to the added lines: each is built so that
    // judging the whole file instead would flip the verdict.
    it('excludes covered lines outside the diff, which would mask uncovered added lines', async () => {
        givenTheReportExists();
        // Added-line ratio 0/2 = 0%; whole-file would be 20/22 = 90.9% and pass.
        const guardrail = coverageGuardrail({
            parseReport: () =>
                reportFor({ coveredLines: lineRange(10, 29), uncoveredLines: [1, 2] })
        });

        const result = await runOn(guardrail, fileAddingLines(2));

        expect(result.status).toBe('fail');
        expect(result.summary).toContain('0.0%');
    });

    it('excludes uncovered lines outside the diff, which would sink covered added lines', async () => {
        givenTheReportExists();
        // Added-line ratio 3/3 = 100%; whole-file would be 3/23 = 13% and fail.
        const guardrail = coverageGuardrail({
            parseReport: () =>
                reportFor({ coveredLines: [1, 2, 3], uncoveredLines: lineRange(10, 29) })
        });

        const result = await runOn(guardrail, fileAddingLines(3));

        expect(result.status).toBe('pass');
        expect(result.summary).toContain('100.0%');
    });

    it('fails a file absent from the report', async () => {
        givenTheReportExists();
        const guardrail = coverageGuardrail({ parseReport: reportListingNoFiles });

        const result = await runOn(guardrail, fileAddingLines(3));

        expect(result.status).toBe('fail');
        expect(result.summary).toContain('not found in coverage report');
        expect(result.summary).toContain(MODEL);
    });

    it('judges each file on its own ratio rather than pooling them', async () => {
        givenTheReportExists();
        const guardrail = coverageGuardrail({
            parseReport: () =>
                reportFor(
                    { path: MODEL, coveredLines: [1, 2, 3], uncoveredLines: [] },
                    { path: SERVICE, coveredLines: [], uncoveredLines: [1, 2, 3] }
                )
        });

        const result = await runOn(
            guardrail,
            fileAddingLines(3, MODEL),
            fileAddingLines(3, SERVICE)
        );

        expect(result.status).toBe('fail');
        expect(result.summary).toContain(`[PASS] ${MODEL}`);
        expect(result.summary).toContain(`[FAIL] ${SERVICE}`);
    });
});
