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

const REPORT_PATH = '/tmp/lightly_studio/coverage.json';

/** The new-file line numbers `PATCH` adds, so a report can name the same lines. */
const ADDED_LINES = [12, 13, 14];
const PATCH = '@@ -12,0 +12,3 @@\n+added line 12\n+added line 13\n+added line 14\n';

// The same file as coverage.py names it (cwd-relative) and as the diff names it.
const COVERAGE_KEY = 'src/lightly_studio/service.py';
const REPO_RELATIVE_KEY = 'lightly_studio/' + COVERAGE_KEY;

const BACKEND_FILE: ChangedFile = {
    path: REPO_RELATIVE_KEY,
    status: 'modified',
    additions: ADDED_LINES.length,
    deletions: 0,
    patch: PATCH
};

type ReportFiles = Record<string, CoverageFileData>;

function makeCtx(files: ChangedFile[]): GuardrailContext {
    return { baseRef: 'origin/main', changedFiles: async () => files };
}

function setReport(files: ReportFiles): void {
    process.env.BACKEND_COVERAGE_JSON = REPORT_PATH;
    mockExistsSync.mockReturnValue(true);
    mockReadFileSync.mockReturnValue(JSON.stringify({ files }));
}

beforeEach(() => {
    vi.resetAllMocks();
});

afterEach(() => {
    delete process.env.BACKEND_COVERAGE_JSON;
    delete process.env.BACKEND_TESTS_PASSED;
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

    // coverage.py cannot see examples/ or the vendored trees (no __init__.py), and
    // neither is code we hold to a coverage bar.
    it.each(['migrations/001_add_table.py', 'examples/example_yolo.py', 'vendor/clip/model.py'])(
        'excludes %s',
        (relative) => {
            const files = [file(`lightly_studio/src/lightly_studio/${relative}`)];
            expect(filterBackendFiles(files)).toHaveLength(0);
        }
    );

    it('returns only matching files from a mixed list', () => {
        const result = filterBackendFiles([
            file('lightly_studio/src/lightly_studio/service.py'),
            file('lightly_studio/src/lightly_studio/__init__.py'),
            file('lightly_studio_view/src/App.svelte')
        ]);
        expect(result.map((f) => f.path)).toEqual([REPO_RELATIVE_KEY]);
    });
});

describe('parseBackendReport', () => {
    it('maps cwd-relative report keys to repo-relative paths', () => {
        const report = parseBackendReport(
            JSON.stringify({
                files: { [COVERAGE_KEY]: { executed_lines: [1], missing_lines: [2] } }
            })
        );
        expect([...report.keys()]).toEqual([REPO_RELATIVE_KEY]);
    });

    it('treats executed and missing lines together as executable', () => {
        const report = parseBackendReport(
            JSON.stringify({
                files: { [COVERAGE_KEY]: { executed_lines: [1, 3], missing_lines: [2] } }
            })
        );
        const entry = report.get(REPO_RELATIVE_KEY);
        expect([...entry!.executable].sort()).toEqual([1, 2, 3]);
        expect([...entry!.covered].sort()).toEqual([1, 3]);
    });
});

describe('backendCoverageGuardrail', () => {
    it('passes immediately when no backend source file changed', async () => {
        const result = await backendCoverageGuardrail.run(
            makeCtx([
                {
                    path: 'lightly_studio_view/src/lib/foo.ts',
                    status: 'modified',
                    additions: ADDED_LINES.length,
                    deletions: 0,
                    patch: PATCH
                }
            ])
        );
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('0 file(s) checked');
    });

    it('skips with an explanatory summary when BACKEND_COVERAGE_JSON is unset', async () => {
        const result = await backendCoverageGuardrail.run(makeCtx([BACKEND_FILE]));
        expect(result.status).toBe('pass');
        expect(result.summary).toContain('coverage skipped: BACKEND_COVERAGE_JSON not set');
    });

    it('fails when BACKEND_TESTS_PASSED is false', async () => {
        setReport({ [COVERAGE_KEY]: { executed_lines: ADDED_LINES, missing_lines: [] } });
        process.env.BACKEND_TESTS_PASSED = 'false';
        const result = await backendCoverageGuardrail.run(makeCtx([BACKEND_FILE]));
        expect(result.status).toBe('fail');
        expect(result.summary).toContain('test suite failed');
    });

    it('passes when all added lines are covered', async () => {
        setReport({ [COVERAGE_KEY]: { executed_lines: ADDED_LINES, missing_lines: [] } });
        const result = await backendCoverageGuardrail.run(makeCtx([BACKEND_FILE]));
        expect(result.status).toBe('pass');
        expect(result.summary).toContain(`[PASS] ${BACKEND_FILE.path}`);
    });

    it('fails an untested new file instead of auto-passing it', async () => {
        setReport({ [COVERAGE_KEY]: { executed_lines: [], missing_lines: ADDED_LINES } });
        const result = await backendCoverageGuardrail.run(
            makeCtx([{ ...BACKEND_FILE, status: 'added' }])
        );
        expect(result.status).toBe('fail');
        expect(result.summary).toContain('0.0%');
    });

    it('fails a changed file the report does not mention', async () => {
        setReport({ 'src/lightly_studio/other.py': { executed_lines: [1], missing_lines: [] } });
        const result = await backendCoverageGuardrail.run(makeCtx([BACKEND_FILE]));
        expect(result.status).toBe('fail');
        expect(result.summary).toContain('not found in coverage report');
    });
});
