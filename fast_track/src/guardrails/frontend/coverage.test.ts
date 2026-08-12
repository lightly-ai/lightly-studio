import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('node:fs', () => ({
    existsSync: vi.fn(),
    readFileSync: vi.fn()
}));

import { existsSync, readFileSync } from 'node:fs';
import { filterFrontendFiles, frontendCoverageGuardrail, parseFrontendReport } from './coverage';
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

// One Istanbul entry for foo.ts. Each statement spans a single line; `hits` maps
// line -> execution count, so { 1: 1, 2: 0 } covers line 1 and misses line 2.
function fooReport(hits: Record<number, number>): string {
    const statementMap: Record<string, unknown> = {};
    const s: Record<string, number> = {};
    Object.entries(hits).forEach(([line, count], idx) => {
        const n = Number(line);
        statementMap[idx] = { start: { line: n, column: 0 }, end: { line: n, column: 10 } };
        s[idx] = count;
    });
    return JSON.stringify({ [`${FRONTEND_ABS}/src/lib/foo.ts`]: { statementMap, s } });
}

function setReport(raw: string): void {
    process.env.FRONTEND_COVERAGE_JSON = '/tmp/lightly_studio_view/coverage/coverage-final.json';
    mockExistsSync.mockReturnValue(true);
    mockReadFileSync.mockReturnValue(raw);
}

beforeEach(() => {
    vi.resetAllMocks();
});

afterEach(() => {
    delete process.env.FRONTEND_COVERAGE_JSON;
    delete process.env.FRONTEND_TESTS_PASSED;
});

describe('filterFrontendFiles', () => {
    function file(path: string): ChangedFile {
        return { path, status: 'modified', additions: 1, deletions: 0 };
    }

    it('keeps source files under the frontend src prefix', () => {
        const files = [file(`${FRONTEND_PREFIX}src/lib/foo.ts`)];
        expect(filterFrontendFiles(files)).toHaveLength(1);
    });

    it('excludes files outside the frontend src prefix', () => {
        const files = [
            file('lightly_studio/src/lightly_studio/service.py'),
            file(`${FRONTEND_PREFIX}vite.config.ts`)
        ];
        expect(filterFrontendFiles(files)).toHaveLength(0);
    });

    it.each([
        'foo.test.ts',
        'foo.test.js',
        'foo.test.svelte',
        'foo.spec.ts',
        'foo.spec.js',
        'foo.spec.svelte',
        'types.d.ts'
    ])('excludes %s', (name) => {
        const files = [file(`${FRONTEND_PREFIX}src/lib/${name}`)];
        expect(filterFrontendFiles(files)).toHaveLength(0);
    });

    it('excludes non-source files (.css, .svg)', () => {
        const files = [
            file(`${FRONTEND_PREFIX}src/app.css`),
            file(`${FRONTEND_PREFIX}src/assets/logo.svg`)
        ];
        expect(filterFrontendFiles(files)).toHaveLength(0);
    });

    it('returns only matching files from a mixed list', () => {
        const result = filterFrontendFiles([
            file(`${FRONTEND_PREFIX}src/lib/foo.ts`),
            file(`${FRONTEND_PREFIX}src/lib/foo.test.ts`),
            file('lightly_studio/src/lightly_studio/service.py')
        ]);
        expect(result.map((f) => f.path)).toEqual([`${FRONTEND_PREFIX}src/lib/foo.ts`]);
    });
});

describe('parseFrontendReport', () => {
    it('maps absolute report keys to repo-relative paths', () => {
        const report = parseFrontendReport(fooReport({ 1: 1 }));
        expect([...report.keys()]).toEqual([`${FRONTEND_PREFIX}src/lib/foo.ts`]);
    });

    it('normalises Windows separators before matching the frontend prefix', () => {
        const report = parseFrontendReport(
            JSON.stringify({
                [`C:\\repo\\${FRONTEND_PREFIX.replace(/\//g, '\\')}src\\lib\\foo.ts`]: {
                    statementMap: {
                        '0': { start: { line: 1, column: 0 }, end: { line: 1, column: 5 } }
                    },
                    s: { '0': 1 }
                }
            })
        );
        expect([...report.keys()]).toEqual([`${FRONTEND_PREFIX}src/lib/foo.ts`]);
    });

    it('skips entries whose path is outside the frontend prefix', () => {
        const report = parseFrontendReport(
            JSON.stringify({
                '/some/other/repo/src/foo.ts': {
                    statementMap: {
                        '0': { start: { line: 1, column: 0 }, end: { line: 1, column: 5 } }
                    },
                    s: { '0': 1 }
                }
            })
        );
        expect(report.size).toBe(0);
    });

    it('marks a line executable if any statement covers it, covered if any covering statement has hits', () => {
        const report = parseFrontendReport(fooReport({ 1: 1, 2: 0 }));
        const entry = report.get(`${FRONTEND_PREFIX}src/lib/foo.ts`);
        expect([...entry!.executable].sort()).toEqual([1, 2]);
        expect([...entry!.covered].sort()).toEqual([1]);
    });

    it('spans every line of a multi-line statement', () => {
        const report = parseFrontendReport(
            JSON.stringify({
                [`${FRONTEND_ABS}/src/lib/foo.ts`]: {
                    statementMap: {
                        '0': { start: { line: 1, column: 0 }, end: { line: 3, column: 10 } }
                    },
                    s: { '0': 2 }
                }
            })
        );
        const entry = report.get(`${FRONTEND_PREFIX}src/lib/foo.ts`);
        expect([...entry!.executable].sort()).toEqual([1, 2, 3]);
        expect([...entry!.covered].sort()).toEqual([1, 2, 3]);
    });

    it('treats a missing s entry as 0 hits', () => {
        const report = parseFrontendReport(
            JSON.stringify({
                [`${FRONTEND_ABS}/src/lib/foo.ts`]: {
                    statementMap: {
                        '0': { start: { line: 1, column: 0 }, end: { line: 1, column: 10 } }
                    },
                    s: {}
                }
            })
        );
        const entry = report.get(`${FRONTEND_PREFIX}src/lib/foo.ts`);
        expect([...entry!.executable]).toEqual([1]);
        expect([...entry!.covered]).toEqual([]);
    });
});

describe('frontendCoverageGuardrail', () => {
    it('passes immediately when no frontend source file changed', async () => {
        const result = await frontendCoverageGuardrail.run(
            makeCtx([
                {
                    path: 'lightly_studio/src/lightly_studio/service.py',
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

    it('skips with an explanatory summary when FRONTEND_COVERAGE_JSON is unset', async () => {
        const result = await frontendCoverageGuardrail.run(makeCtx([FRONTEND_FILE]));
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('coverage skipped: FRONTEND_COVERAGE_JSON not set');
    });

    it('fails when FRONTEND_TESTS_PASSED is false', async () => {
        setReport(fooReport({ 1: 1, 2: 1, 3: 1 }));
        process.env.FRONTEND_TESTS_PASSED = 'false';
        const result = await frontendCoverageGuardrail.run(makeCtx([FRONTEND_FILE]));
        expect(result.status).toBe('fail');
        expect(result.summary).toContain('test suite failed');
    });

    it('passes when all added lines are covered', async () => {
        setReport(fooReport({ 1: 1, 2: 1, 3: 1 }));
        const result = await frontendCoverageGuardrail.run(makeCtx([FRONTEND_FILE]));
        expect(result.status).toBe('pass');
        expect(result.summary).toContain(`[PASS] ${FRONTEND_FILE.path}`);
    });

    it('fails an untested new file instead of auto-passing it', async () => {
        setReport(fooReport({ 1: 0, 2: 0, 3: 0 }));
        const result = await frontendCoverageGuardrail.run(
            makeCtx([{ ...FRONTEND_FILE, status: 'added' }])
        );
        expect(result.status).toBe('fail');
        expect(result.summary).toContain('0.0%');
    });

    it('fails a changed file the report does not mention', async () => {
        setReport(
            JSON.stringify({
                [`${FRONTEND_ABS}/src/lib/other.ts`]: {
                    statementMap: {
                        '0': { start: { line: 1, column: 0 }, end: { line: 1, column: 10 } }
                    },
                    s: { '0': 1 }
                }
            })
        );
        const result = await frontendCoverageGuardrail.run(makeCtx([FRONTEND_FILE]));
        expect(result.status).toBe('fail');
        expect(result.summary).toContain('not found in coverage report');
    });
});
