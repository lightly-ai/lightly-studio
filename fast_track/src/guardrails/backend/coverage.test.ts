import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('node:fs', () => ({
    existsSync: vi.fn(),
    readFileSync: vi.fn()
}));

import { existsSync, readFileSync } from 'node:fs';
import {
    backendCoverageGuardrail,
    filterBackendFiles,
    parseBackendReport,
    type CoverageFileData
} from './coverage';
import type { ChangedFile, GuardrailContext } from '../context/types';

const mockExistsSync = vi.mocked(existsSync);
const mockReadFileSync = vi.mocked(readFileSync);

function makeCtx(files: ChangedFile[]): GuardrailContext {
    return { changedFiles: async () => files };
}

const reports = new Map<string, string>();

function setReport(
    envVar: string,
    reportPath: string,
    files: Record<string, CoverageFileData>
): void {
    process.env[envVar] = reportPath;
    reports.set(reportPath, JSON.stringify({ files }));
    mockExistsSync.mockImplementation((path) => reports.has(String(path)));
    mockReadFileSync.mockImplementation((path) => reports.get(String(path)) ?? '');
}

function setStudioReport(files: Record<string, CoverageFileData>): void {
    setReport('BACKEND_COVERAGE_JSON', '/tmp/lightly_studio/coverage.json', files);
}

function setServeReport(files: Record<string, CoverageFileData>): void {
    setReport('BACKEND_SERVE_COVERAGE_JSON', '/tmp/lightly_studio_serve/coverage.json', files);
}

const STUDIO_SERVICE = 'lightly_studio/src/lightly_studio/service.py';
const SERVE_SERVER = 'lightly_studio_serve/src/lightly_studio_serve/server.py';

function setCoveredStudioReport(): void {
    setStudioReport({
        'src/lightly_studio/service.py': { executed_lines: [12, 13, 14], missing_lines: [] }
    });
}

function setUncoveredServeReport(): void {
    setServeReport({
        'src/lightly_studio_serve/server.py': { executed_lines: [], missing_lines: [12, 13, 14] }
    });
}

beforeEach(() => {
    vi.resetAllMocks();
    reports.clear();
});

afterEach(() => {
    delete process.env.BACKEND_COVERAGE_JSON;
    delete process.env.BACKEND_TESTS_PASSED;
    delete process.env.BACKEND_SERVE_COVERAGE_JSON;
    delete process.env.BACKEND_SERVE_TESTS_PASSED;
});

describe('filterBackendFiles', () => {
    function file(path: string): ChangedFile {
        return { path, status: 'modified', additions: 1, deletions: 0 };
    }

    it('keeps .py files under the backend prefix', () => {
        const files = [file('lightly_studio/src/lightly_studio/models/dataset.py')];
        expect(filterBackendFiles(files)).toHaveLength(1);
    });

    it('excludes files outside the backend prefix', () => {
        const files = [
            file('lightly_studio_view/src/components/Button.svelte'),
            file('lightly_studio/tests/test_model.py')
        ];
        expect(filterBackendFiles(files)).toHaveLength(0);
    });

    it('excludes non-.py files under the backend prefix', () => {
        const files = [file('lightly_studio/src/lightly_studio/models/schema.json')];
        expect(filterBackendFiles(files)).toHaveLength(0);
    });

    it('excludes test_ files under the backend prefix', () => {
        const files = [file('lightly_studio/src/lightly_studio/models/test_dataset.py')];
        expect(filterBackendFiles(files)).toHaveLength(0);
    });

    it('excludes conftest.py', () => {
        const files = [file('lightly_studio/src/lightly_studio/conftest.py')];
        expect(filterBackendFiles(files)).toHaveLength(0);
    });

    it('excludes __init__.py', () => {
        const files = [file('lightly_studio/src/lightly_studio/models/__init__.py')];
        expect(filterBackendFiles(files)).toHaveLength(0);
    });

    // examples/ has no __init__.py, so coverage.py cannot see it; vendored code is
    // third-party.
    it.each(['migrations/001_add_table.py', 'examples/example_yolo.py', 'vendor/clip/model.py'])(
        'excludes %s',
        (relative) => {
            const files = [file(`lightly_studio/src/lightly_studio/${relative}`)];
            expect(filterBackendFiles(files)).toHaveLength(0);
        }
    );

    it('keeps .py files under a sibling member', () => {
        const files = [file('lightly_studio_serve/src/lightly_studio_serve/server.py')];
        expect(filterBackendFiles(files)).toHaveLength(1);
    });

    it('excludes the tests of a sibling member', () => {
        const files = [file('lightly_studio_serve/tests/test_server.py')];
        expect(filterBackendFiles(files)).toHaveLength(0);
    });

    it('returns only matching files from a mixed list', () => {
        const result = filterBackendFiles([
            file('lightly_studio/src/lightly_studio/service.py'),
            file('lightly_studio/src/lightly_studio/__init__.py'),
            file('lightly_studio_view/src/App.svelte')
        ]);
        expect(result.map((f) => f.path)).toEqual(['lightly_studio/src/lightly_studio/service.py']);
    });
});

describe('parseBackendReport', () => {
    it('maps cwd-relative report keys to repo-relative paths', () => {
        const report = parseBackendReport(
            JSON.stringify({
                files: {
                    'src/lightly_studio/service.py': { executed_lines: [1], missing_lines: [2] }
                }
            }),
            'lightly_studio/'
        );
        expect([...report.keys()]).toEqual(['lightly_studio/src/lightly_studio/service.py']);
    });

    it('treats executed and missing lines together as executable', () => {
        const report = parseBackendReport(
            JSON.stringify({
                files: {
                    'src/lightly_studio/service.py': { executed_lines: [1, 3], missing_lines: [2] }
                }
            }),
            'lightly_studio/'
        );
        const entry = report.get('lightly_studio/src/lightly_studio/service.py');
        expect([...entry!.executable].sort()).toEqual([1, 2, 3]);
        expect([...entry!.covered].sort()).toEqual([1, 3]);
    });

    it('keys the report of a sibling member against that member', () => {
        const report = parseBackendReport(
            JSON.stringify({
                files: {
                    'src/lightly_studio_serve/server.py': {
                        executed_lines: [1],
                        missing_lines: []
                    }
                }
            }),
            'lightly_studio_serve/'
        );
        expect([...report.keys()]).toEqual([
            'lightly_studio_serve/src/lightly_studio_serve/server.py'
        ]);
    });
});

describe('backendCoverageGuardrail', () => {
    function changed(path: string): ChangedFile {
        return {
            path,
            status: 'modified',
            additions: 3,
            deletions: 0,
            patch: '@@ -12,0 +12,3 @@\n+added line 12\n+added line 13\n+added line 14\n'
        };
    }

    it('passes immediately when no backend source file changed', async () => {
        const result = await backendCoverageGuardrail.run(
            makeCtx([
                {
                    path: 'lightly_studio_view/src/lib/foo.ts',
                    status: 'modified',
                    additions: 3,
                    deletions: 0,
                    patch: '@@ -12,0 +12,3 @@\n+added line 12\n+added line 13\n+added line 14\n'
                }
            ])
        );
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('0 file(s) checked');
    });

    it('skips with an explanatory summary when BACKEND_COVERAGE_JSON is unset', async () => {
        const result = await backendCoverageGuardrail.run(
            makeCtx([
                {
                    path: 'lightly_studio/src/lightly_studio/service.py',
                    status: 'modified',
                    additions: 3,
                    deletions: 0,
                    patch: '@@ -12,0 +12,3 @@\n+added line 12\n+added line 13\n+added line 14\n'
                }
            ])
        );
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('coverage skipped: BACKEND_COVERAGE_JSON not set');
    });

    it('fails when BACKEND_TESTS_PASSED is false', async () => {
        setCoveredStudioReport();
        process.env.BACKEND_TESTS_PASSED = 'false';
        const result = await backendCoverageGuardrail.run(
            makeCtx([
                {
                    path: 'lightly_studio/src/lightly_studio/service.py',
                    status: 'modified',
                    additions: 3,
                    deletions: 0,
                    patch: '@@ -12,0 +12,3 @@\n+added line 12\n+added line 13\n+added line 14\n'
                }
            ])
        );
        expect(result.status).toBe('fail');
        expect(result.summary).toContain('test suite failed');
    });

    it('passes when all added lines are covered', async () => {
        setCoveredStudioReport();
        const result = await backendCoverageGuardrail.run(
            makeCtx([
                {
                    path: 'lightly_studio/src/lightly_studio/service.py',
                    status: 'modified',
                    additions: 3,
                    deletions: 0,
                    patch: '@@ -12,0 +12,3 @@\n+added line 12\n+added line 13\n+added line 14\n'
                }
            ])
        );
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('[PASS] lightly_studio/src/lightly_studio/service.py');
    });

    it('fails an untested new file instead of auto-passing it', async () => {
        setStudioReport({
            'src/lightly_studio/service.py': { executed_lines: [], missing_lines: [12, 13, 14] }
        });
        const result = await backendCoverageGuardrail.run(
            makeCtx([
                {
                    path: 'lightly_studio/src/lightly_studio/service.py',
                    status: 'added',
                    additions: 3,
                    deletions: 0,
                    patch: '@@ -12,0 +12,3 @@\n+added line 12\n+added line 13\n+added line 14\n'
                }
            ])
        );
        expect(result.status).toBe('fail');
        expect(result.summary).toContain('0.0%');
    });

    it('fails a changed file the report does not mention', async () => {
        setStudioReport({
            'src/lightly_studio/other.py': { executed_lines: [1], missing_lines: [] }
        });
        const result = await backendCoverageGuardrail.run(
            makeCtx([
                {
                    path: 'lightly_studio/src/lightly_studio/service.py',
                    status: 'modified',
                    additions: 3,
                    deletions: 0,
                    patch: '@@ -12,0 +12,3 @@\n+added line 12\n+added line 13\n+added line 14\n'
                }
            ])
        );
        expect(result.status).toBe('fail');
        expect(result.summary).toContain('not found in coverage report');
    });

    it('judges a sibling member against its own report', async () => {
        setUncoveredServeReport();
        const result = await backendCoverageGuardrail.run(makeCtx([changed(SERVE_SERVER)]));
        expect(result.status).toBe('fail');
        expect(result.summary).toContain(`[FAIL] ${SERVE_SERVER}`);
    });

    it('reports every member a pull request touches in one summary', async () => {
        setCoveredStudioReport();
        setUncoveredServeReport();
        const result = await backendCoverageGuardrail.run(
            makeCtx([changed(STUDIO_SERVICE), changed(SERVE_SERVER)])
        );
        expect(result.status).toBe('fail');
        expect(result.summary).toContain(`[PASS] ${STUDIO_SERVICE}`);
        expect(result.summary).toContain(`[FAIL] ${SERVE_SERVER}`);
    });

    it('ignores a member the pull request does not touch', async () => {
        setCoveredStudioReport();
        const result = await backendCoverageGuardrail.run(makeCtx([changed(STUDIO_SERVICE)]));
        expect(result.status).toBe('pass');
        expect(result.summary).not.toContain('BACKEND_SERVE_COVERAGE_JSON');
    });
});
