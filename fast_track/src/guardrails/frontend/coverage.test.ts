import { beforeEach, describe, expect, it, vi } from 'vitest';

// Hoist before mocks so the factory can reference it.
const mockExecFile = vi.hoisted(() => vi.fn());

vi.mock('node:fs', () => ({
    existsSync: vi.fn(),
    readFileSync: vi.fn()
}));

vi.mock('node:child_process', () => ({
    execFile: mockExecFile
}));

import { existsSync, readFileSync } from 'node:fs';
import { fileCoverageRatio, frontendCoverageGuardrail } from './coverage';
import { FRONTEND_ABS, FRONTEND_PREFIX } from './eslint-runner';
import type { ChangedFile, GuardrailContext } from '../context/types';

const mockExistsSync = vi.mocked(existsSync);
const mockReadFileSync = vi.mocked(readFileSync);

// Minimal patch that adds lines 1–3.
const PATCH = '@@ -0,0 +1,3 @@\n+line 1\n+line 2\n+line 3\n';

function makeCtx(files: ChangedFile[]): GuardrailContext {
    return { baseRef: 'origin/main', changedFiles: async () => files };
}

const FRONTEND_FILE: ChangedFile = {
    path: `${FRONTEND_PREFIX}src/lib/foo.ts`,
    status: 'modified',
    additions: 3,
    deletions: 0,
    patch: PATCH
};

// Coverage data where lines 1–3 of foo.ts are fully covered.
const FULL_COVERAGE_DATA = {
    [`${FRONTEND_ABS}/src/lib/foo.ts`]: {
        statementMap: {
            '0': { start: { line: 1, column: 0 }, end: { line: 1, column: 10 } },
            '1': { start: { line: 2, column: 0 }, end: { line: 2, column: 10 } },
            '2': { start: { line: 3, column: 0 }, end: { line: 3, column: 10 } }
        },
        s: { '0': 1, '1': 1, '2': 1 }
    }
};

// Makes execFile call its callback immediately with success or failure.
function mockExecFileWith(error: Error | null): void {
    mockExecFile.mockImplementation((...args: unknown[]) => {
        (args[args.length - 1] as (err: Error | null, stdout: string, stderr: string) => void)(
            error,
            '',
            ''
        );
    });
}

// Sets up the two existsSync calls for a full successful run:
//   1. .test.ts candidate exists (findFrontendTestFile)
//   2. coverage JSON was produced (runTests)
function setupSuccessfulRun(coverageData: object = FULL_COVERAGE_DATA): void {
    mockExistsSync.mockReturnValueOnce(true).mockReturnValueOnce(true);
    mockExecFileWith(null);
    mockReadFileSync.mockReturnValue(JSON.stringify(coverageData));
}

beforeEach(() => {
    vi.resetAllMocks();
});

describe('fileCoverageRatio', () => {
    it('returns null when addedLines is empty', () => {
        const entry = {
            statementMap: { '0': { start: { line: 1, column: 0 }, end: { line: 1, column: 10 } } },
            s: { '0': 1 }
        };
        expect(fileCoverageRatio(entry, new Set())).toBeNull();
    });

    it('returns null when no added line overlaps any statement', () => {
        const entry = {
            statementMap: { '0': { start: { line: 1, column: 0 }, end: { line: 1, column: 10 } } },
            s: { '0': 1 }
        };
        expect(fileCoverageRatio(entry, new Set([5, 6]))).toBeNull();
    });

    it('returns 1 when all added lines are covered', () => {
        const entry = {
            statementMap: {
                '0': { start: { line: 1, column: 0 }, end: { line: 1, column: 10 } },
                '1': { start: { line: 2, column: 0 }, end: { line: 2, column: 10 } }
            },
            s: { '0': 1, '1': 3 }
        };
        expect(fileCoverageRatio(entry, new Set([1, 2]))).toBe(1);
    });

    it('returns 0 when all added lines are uncovered', () => {
        const entry = {
            statementMap: {
                '0': { start: { line: 1, column: 0 }, end: { line: 1, column: 10 } },
                '1': { start: { line: 2, column: 0 }, end: { line: 2, column: 10 } }
            },
            s: { '0': 0, '1': 0 }
        };
        expect(fileCoverageRatio(entry, new Set([1, 2]))).toBe(0);
    });

    it('returns fractional ratio for partial coverage', () => {
        const entry = {
            statementMap: {
                '0': { start: { line: 1, column: 0 }, end: { line: 1, column: 10 } },
                '1': { start: { line: 2, column: 0 }, end: { line: 2, column: 10 } },
                '2': { start: { line: 3, column: 0 }, end: { line: 3, column: 10 } },
                '3': { start: { line: 4, column: 0 }, end: { line: 4, column: 10 } }
            },
            s: { '0': 1, '1': 1, '2': 0, '3': 0 }
        };
        expect(fileCoverageRatio(entry, new Set([1, 2, 3, 4]))).toBe(0.5);
    });

    it('counts each line of a multi-line statement separately', () => {
        const entry = {
            statementMap: {
                '0': { start: { line: 1, column: 0 }, end: { line: 3, column: 10 } }
            },
            s: { '0': 1 }
        };
        // Statement spans lines 1–3; all three are in addedLines and all covered.
        expect(fileCoverageRatio(entry, new Set([1, 2, 3]))).toBe(1);
    });

    it('only scores lines that appear in addedLines for multi-line statements', () => {
        const entry = {
            statementMap: {
                '0': { start: { line: 1, column: 0 }, end: { line: 3, column: 10 } }
            },
            s: { '0': 0 }
        };
        // Statement spans lines 1–3 but only line 2 was added; it is not covered.
        expect(fileCoverageRatio(entry, new Set([2]))).toBe(0);
    });

    it('treats a missing s entry as 0 hits', () => {
        const entry = {
            statementMap: {
                '0': { start: { line: 1, column: 0 }, end: { line: 1, column: 10 } }
            },
            s: {}
        };
        expect(fileCoverageRatio(entry, new Set([1]))).toBe(0);
    });
});

describe('frontendCoverageGuardrail – filterFiles', () => {
    it('passes immediately when only backend files changed', async () => {
        const result = await frontendCoverageGuardrail.run(
            makeCtx([
                {
                    path: 'lightly_studio/src/model.py',
                    status: 'modified',
                    additions: 3,
                    deletions: 0,
                    patch: PATCH
                }
            ])
        );
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('0 file(s) checked');
    });

    it('filters out .test.ts files', async () => {
        const result = await frontendCoverageGuardrail.run(
            makeCtx([
                {
                    path: `${FRONTEND_PREFIX}src/lib/foo.test.ts`,
                    status: 'modified',
                    additions: 3,
                    deletions: 0,
                    patch: PATCH
                }
            ])
        );
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('0 file(s) checked');
    });

    it('filters out .spec.ts files', async () => {
        const result = await frontendCoverageGuardrail.run(
            makeCtx([
                {
                    path: `${FRONTEND_PREFIX}src/lib/foo.spec.ts`,
                    status: 'modified',
                    additions: 3,
                    deletions: 0,
                    patch: PATCH
                }
            ])
        );
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('0 file(s) checked');
    });

    it('filters out .d.ts files', async () => {
        const result = await frontendCoverageGuardrail.run(
            makeCtx([
                {
                    path: `${FRONTEND_PREFIX}src/lib/types.d.ts`,
                    status: 'modified',
                    additions: 3,
                    deletions: 0,
                    patch: PATCH
                }
            ])
        );
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('0 file(s) checked');
    });

    it('filters out non-source files (.css, .svg)', async () => {
        const nonSourceFiles: ChangedFile[] = [
            {
                path: `${FRONTEND_PREFIX}src/app.css`,
                status: 'modified',
                additions: 3,
                deletions: 0,
                patch: PATCH
            },
            {
                path: `${FRONTEND_PREFIX}src/assets/logo.svg`,
                status: 'modified',
                additions: 3,
                deletions: 0,
                patch: PATCH
            }
        ];
        const result = await frontendCoverageGuardrail.run(makeCtx(nonSourceFiles));
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('0 file(s) checked');
    });

    it('includes regular .ts files in the frontend src directory', async () => {
        setupSuccessfulRun();
        const result = await frontendCoverageGuardrail.run(makeCtx([FRONTEND_FILE]));
        expect(result.summary).not.toContain('0 file(s) checked');
    });
});

describe('frontendCoverageGuardrail – findTestFile', () => {
    it('fails when no test file candidate exists on disk', async () => {
        mockExistsSync.mockReturnValue(false); // all test file candidates missing
        const result = await frontendCoverageGuardrail.run(makeCtx([FRONTEND_FILE]));
        expect(result.status).toBe('fail');
        expect(result.summary).toContain('no test file found');
        expect(result.summary).toContain(FRONTEND_FILE.path);
    });

    it('uses the first matching candidate (.test.ts)', async () => {
        setupSuccessfulRun();
        await frontendCoverageGuardrail.run(makeCtx([FRONTEND_FILE]));
        const paths = mockExistsSync.mock.calls.map(([p]) => p as string);
        expect(paths.some((p) => p.endsWith('foo.test.ts'))).toBe(true);
    });

    it('skips candidates that do not exist and uses the next match (.spec.ts)', async () => {
        mockExistsSync
            .mockReturnValueOnce(false) // foo.test.ts not found
            .mockReturnValueOnce(false) // foo.test.js not found
            .mockReturnValueOnce(true) // foo.spec.ts found
            .mockReturnValueOnce(true); // coverage JSON exists
        mockExecFileWith(null);
        mockReadFileSync.mockReturnValue(JSON.stringify(FULL_COVERAGE_DATA));

        const result = await frontendCoverageGuardrail.run(makeCtx([FRONTEND_FILE]));

        expect(result.status).toBe('pass');
        const paths = mockExistsSync.mock.calls.map(([p]) => p as string);
        expect(paths.some((p) => p.endsWith('foo.spec.ts'))).toBe(true);
    });
});

describe('frontendCoverageGuardrail – runTests', () => {
    it('fails when vitest does not produce a coverage file', async () => {
        mockExistsSync
            .mockReturnValueOnce(true) // test file candidate exists
            .mockReturnValueOnce(false); // coverage JSON not produced
        mockExecFileWith(null);

        const result = await frontendCoverageGuardrail.run(makeCtx([FRONTEND_FILE]));

        expect(result.status).toBe('fail');
        expect(result.summary).toContain('coverage data not found');
    });

    it('invokes vitest via npm run test:unit from lightly_studio_view', async () => {
        setupSuccessfulRun();
        await frontendCoverageGuardrail.run(makeCtx([FRONTEND_FILE]));
        const [cmd, args] = mockExecFile.mock.calls[0]! as [string, string[]];
        expect(cmd).toBe('npm');
        expect(args).toContain('test:unit');
    });

    it('still reads coverage when vitest exits non-zero', async () => {
        mockExistsSync
            .mockReturnValueOnce(true) // test file candidate exists
            .mockReturnValueOnce(true); // coverage JSON written despite failure
        mockExecFileWith(new Error('Tests failed'));
        mockReadFileSync.mockReturnValue(JSON.stringify(FULL_COVERAGE_DATA));

        const result = await frontendCoverageGuardrail.run(makeCtx([FRONTEND_FILE]));

        expect(result.status).toBe('pass');
    });
});

describe('frontendCoverageGuardrail – parseCoverageRatio', () => {
    it('auto-passes when coverage data contains no entry for the source file', async () => {
        setupSuccessfulRun({ [`${FRONTEND_ABS}/src/lib/other.ts`]: { statementMap: {}, s: {} } });
        const result = await frontendCoverageGuardrail.run(makeCtx([FRONTEND_FILE]));
        expect(result.status).toBe('pass');
    });

    it('passes when coverage matches via the FRONTEND_PREFIX suffix of the absolute path', async () => {
        setupSuccessfulRun(FULL_COVERAGE_DATA);
        const result = await frontendCoverageGuardrail.run(makeCtx([FRONTEND_FILE]));
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('[PASS]');
        expect(result.summary).toContain(FRONTEND_FILE.path);
    });

    it('fails when added-line coverage is below 80%', async () => {
        const lowCoverageData = {
            [`${FRONTEND_ABS}/src/lib/foo.ts`]: {
                statementMap: {
                    '0': { start: { line: 1, column: 0 }, end: { line: 1, column: 10 } },
                    '1': { start: { line: 2, column: 0 }, end: { line: 2, column: 10 } },
                    '2': { start: { line: 3, column: 0 }, end: { line: 3, column: 10 } }
                },
                s: { '0': 1, '1': 0, '2': 0 } // 1/3 ≈ 33%
            }
        };
        setupSuccessfulRun(lowCoverageData);
        const result = await frontendCoverageGuardrail.run(makeCtx([FRONTEND_FILE]));
        expect(result.status).toBe('fail');
        expect(result.summary).toContain('[FAIL]');
        expect(result.summary).toContain(FRONTEND_FILE.path);
    });
});
