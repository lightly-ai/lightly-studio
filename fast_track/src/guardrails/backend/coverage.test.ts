import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockExecFile = vi.hoisted(() => vi.fn());

vi.mock('node:fs', () => ({
    existsSync: vi.fn(),
    readFileSync: vi.fn(),
    rmSync: vi.fn()
}));

vi.mock('node:fs/promises', () => ({
    readdir: vi.fn()
}));

vi.mock('node:child_process', () => ({
    execFile: mockExecFile
}));

import { existsSync, readFileSync, rmSync } from 'node:fs';
import { readdir } from 'node:fs/promises';
import { resolve } from 'node:path';
import {
    backendCoverageGuardrail,
    filterBackendFiles,
    matchesTestFile,
    parseCoverageRatio
} from './coverage';
import { REPO_ROOT } from './shared';
import type { ChangedFile, GuardrailContext } from '../context/types';

const mockExistsSync = vi.mocked(existsSync);
const mockReadFileSync = vi.mocked(readFileSync);
const mockRmSync = vi.mocked(rmSync);
const mockReaddir = vi.mocked(readdir);

const LIGHTLY_STUDIO_ABS = resolve(REPO_ROOT, 'lightly_studio');
const TESTS_DIR = resolve(LIGHTLY_STUDIO_ABS, 'tests');
const COVERAGE_PATH = resolve(LIGHTLY_STUDIO_ABS, 'coverage.json');

const PATCH = '@@ -0,0 +1,3 @@\n+line 1\n+line 2\n+line 3\n';

const BACKEND_FILE: ChangedFile = {
    path: 'lightly_studio/src/lightly_studio/service.py',
    status: 'modified',
    additions: 3,
    deletions: 0,
    patch: PATCH
};

const COVERAGE_KEY = 'src/lightly_studio/service.py';

const FULL_COVERAGE_DATA = {
    files: {
        [COVERAGE_KEY]: {
            executed_lines: [1, 2, 3],
            missing_lines: []
        }
    }
};

function makeCtx(files: ChangedFile[]): GuardrailContext {
    return { baseRef: 'origin/main', changedFiles: async () => files };
}

function mockExecFileWith(error: Error | null): void {
    mockExecFile.mockImplementation((...args: unknown[]) => {
        (args[args.length - 1] as (err: Error | null, stdout: string, stderr: string) => void)(
            error,
            '',
            ''
        );
    });
}

function setupTestFileFound(): void {
    mockReaddir.mockResolvedValue([
        { isFile: () => true, name: 'test_service.py', parentPath: TESTS_DIR }
    ] as never);
}

beforeEach(() => {
    vi.resetAllMocks();
});

describe('filterBackendFiles', () => {
    it('keeps .py files under the backend prefix', () => {
        const files: ChangedFile[] = [
            {
                path: 'lightly_studio/src/lightly_studio/models/dataset.py',
                status: 'modified',
                additions: 5,
                deletions: 0
            }
        ];
        expect(filterBackendFiles(files)).toHaveLength(1);
    });

    it('excludes files outside the backend prefix', () => {
        const files: ChangedFile[] = [
            {
                path: 'lightly_studio_view/src/components/Button.svelte',
                status: 'modified',
                additions: 1,
                deletions: 0
            },
            {
                path: 'lightly_studio/tests/test_model.py',
                status: 'modified',
                additions: 1,
                deletions: 0
            }
        ];
        expect(filterBackendFiles(files)).toHaveLength(0);
    });

    it('excludes non-.py files under the backend prefix', () => {
        const files: ChangedFile[] = [
            {
                path: 'lightly_studio/src/lightly_studio/models/schema.json',
                status: 'modified',
                additions: 1,
                deletions: 0
            }
        ];
        expect(filterBackendFiles(files)).toHaveLength(0);
    });

    it('excludes test_ files under the backend prefix', () => {
        const files: ChangedFile[] = [
            {
                path: 'lightly_studio/src/lightly_studio/models/test_dataset.py',
                status: 'modified',
                additions: 5,
                deletions: 0
            }
        ];
        expect(filterBackendFiles(files)).toHaveLength(0);
    });

    it('excludes conftest.py', () => {
        const files: ChangedFile[] = [
            {
                path: 'lightly_studio/src/lightly_studio/conftest.py',
                status: 'modified',
                additions: 2,
                deletions: 0
            }
        ];
        expect(filterBackendFiles(files)).toHaveLength(0);
    });

    it('excludes __init__.py', () => {
        const files: ChangedFile[] = [
            {
                path: 'lightly_studio/src/lightly_studio/models/__init__.py',
                status: 'modified',
                additions: 1,
                deletions: 0
            }
        ];
        expect(filterBackendFiles(files)).toHaveLength(0);
    });

    it('excludes files under migrations/', () => {
        const files: ChangedFile[] = [
            {
                path: 'lightly_studio/src/lightly_studio/migrations/001_add_table.py',
                status: 'modified',
                additions: 10,
                deletions: 0
            }
        ];
        expect(filterBackendFiles(files)).toHaveLength(0);
    });

    it('returns only matching files from a mixed list', () => {
        const files: ChangedFile[] = [
            {
                path: 'lightly_studio/src/lightly_studio/service.py',
                status: 'modified',
                additions: 3,
                deletions: 0
            },
            {
                path: 'lightly_studio/src/lightly_studio/__init__.py',
                status: 'modified',
                additions: 1,
                deletions: 0
            },
            {
                path: 'lightly_studio_view/src/App.svelte',
                status: 'modified',
                additions: 1,
                deletions: 0
            }
        ];
        const result = filterBackendFiles(files);
        expect(result).toHaveLength(1);
        expect(result[0]!.path).toBe('lightly_studio/src/lightly_studio/service.py');
    });
});

describe('matchesTestFile', () => {
    const prefix = 'test_image_dataset';

    it('matches exact test file', () => {
        expect(matchesTestFile('test_image_dataset.py', prefix)).toBe(true);
    });

    it('matches double-underscore suffix variant', () => {
        expect(matchesTestFile('test_image_dataset__yolo.py', prefix)).toBe(true);
        expect(matchesTestFile('test_image_dataset__coco.py', prefix)).toBe(true);
    });

    it('matches single-underscore suffix variant', () => {
        expect(matchesTestFile('test_image_dataset_export.py', prefix)).toBe(true);
    });

    it('does not match unrelated test file', () => {
        expect(matchesTestFile('test_image.py', prefix)).toBe(false);
    });

    it('does not match non-.py file', () => {
        expect(matchesTestFile('test_image_dataset.ts', prefix)).toBe(false);
    });
});

describe('parseCoverageRatio', () => {
    const sourcePath = 'lightly_studio/src/lightly_studio/service.py';
    // coverage.json keys are relative to lightly_studio/, so strip prefix
    const coverageKey = 'src/lightly_studio/service.py';

    it('returns null when the file is not present in coverage data', () => {
        const data = { files: {} };
        const result = parseCoverageRatio(data, sourcePath, new Set([1, 2, 3]));
        expect(result).toBeNull();
    });

    it('returns null when no added lines are executable', () => {
        const data = {
            files: {
                [coverageKey]: {
                    executed_lines: [10, 11],
                    missing_lines: [12]
                }
            }
        };
        // Added lines 1–3 are not in executed or missing
        const result = parseCoverageRatio(data, sourcePath, new Set([1, 2, 3]));
        expect(result).toBeNull();
    });

    it('returns 1.0 when all added executable lines are covered', () => {
        const data = {
            files: {
                [coverageKey]: {
                    executed_lines: [1, 2, 3],
                    missing_lines: []
                }
            }
        };
        const result = parseCoverageRatio(data, sourcePath, new Set([1, 2, 3]));
        expect(result).toBe(1.0);
    });

    it('returns 0.0 when all added executable lines are missing', () => {
        const data = {
            files: {
                [coverageKey]: {
                    executed_lines: [],
                    missing_lines: [1, 2, 3]
                }
            }
        };
        const result = parseCoverageRatio(data, sourcePath, new Set([1, 2, 3]));
        expect(result).toBe(0.0);
    });

    it('returns partial ratio when some added lines are covered', () => {
        const data = {
            files: {
                [coverageKey]: {
                    executed_lines: [1, 2],
                    missing_lines: [3, 4]
                }
            }
        };
        // Added lines: 1, 2, 3, 4 — 2 covered out of 4 executable
        const result = parseCoverageRatio(data, sourcePath, new Set([1, 2, 3, 4]));
        expect(result).toBe(0.5);
    });

    it('only counts added lines, ignoring non-added executable lines', () => {
        const data = {
            files: {
                [coverageKey]: {
                    executed_lines: [1, 2, 10, 11],
                    missing_lines: [3, 4, 12]
                }
            }
        };
        // Only lines 1–4 were added; lines 10–12 should not affect the ratio
        const result = parseCoverageRatio(data, sourcePath, new Set([1, 2, 3, 4]));
        expect(result).toBe(0.5);
    });
});

describe('backendCoverageGuardrail – runTests', () => {
    it('deletes stale coverage.json before running pytest', async () => {
        mockExistsSync
            .mockReturnValueOnce(true) // testsDir exists (findTestFile)
            .mockReturnValueOnce(true) // stale coveragePath exists → rmSync
            .mockReturnValueOnce(true); // coveragePath exists after run
        setupTestFileFound();
        mockExecFileWith(null);
        mockReadFileSync.mockReturnValue(JSON.stringify(FULL_COVERAGE_DATA));

        await backendCoverageGuardrail.run(makeCtx([BACKEND_FILE]));

        expect(mockRmSync).toHaveBeenCalledOnce();
        expect(mockRmSync).toHaveBeenCalledWith(COVERAGE_PATH);
    });

    it('does not delete coverage.json when none exists before the run', async () => {
        mockExistsSync
            .mockReturnValueOnce(true) // testsDir exists
            .mockReturnValueOnce(false) // no stale coverage file
            .mockReturnValueOnce(true); // coverage written after run
        setupTestFileFound();
        mockExecFileWith(null);
        mockReadFileSync.mockReturnValue(JSON.stringify(FULL_COVERAGE_DATA));

        await backendCoverageGuardrail.run(makeCtx([BACKEND_FILE]));

        expect(mockRmSync).not.toHaveBeenCalled();
    });

    it('reads coverage.json written by pytest even when tests fail', async () => {
        mockExistsSync
            .mockReturnValueOnce(true) // testsDir exists
            .mockReturnValueOnce(false) // no stale file
            .mockReturnValueOnce(true) // coverage exists in catch block
            .mockReturnValueOnce(true); // coverage exists after catch
        setupTestFileFound();
        mockExecFileWith(new Error('Tests failed'));
        mockReadFileSync.mockReturnValue(JSON.stringify(FULL_COVERAGE_DATA));

        const result = await backendCoverageGuardrail.run(makeCtx([BACKEND_FILE]));

        expect(result.status).toBe('pass');
        expect(mockReadFileSync).toHaveBeenCalled();
    });

    it('re-throws error when pytest fails without writing coverage.json', async () => {
        mockExistsSync
            .mockReturnValueOnce(true) // testsDir exists
            .mockReturnValueOnce(false) // no stale file
            .mockReturnValueOnce(false); // no coverage in catch → re-throw
        setupTestFileFound();
        mockExecFileWith(new Error('uv: command not found'));

        await expect(backendCoverageGuardrail.run(makeCtx([BACKEND_FILE]))).rejects.toThrow(
            'uv: command not found'
        );
    });

    it('passes when all added lines are covered', async () => {
        mockExistsSync
            .mockReturnValueOnce(true)
            .mockReturnValueOnce(false)
            .mockReturnValueOnce(true);
        setupTestFileFound();
        mockExecFileWith(null);
        mockReadFileSync.mockReturnValue(JSON.stringify(FULL_COVERAGE_DATA));

        const result = await backendCoverageGuardrail.run(makeCtx([BACKEND_FILE]));

        expect(result.status).toBe('pass');
        expect(result.summary).toContain('[PASS]');
        expect(result.summary).toContain(BACKEND_FILE.path);
    });

    it('fails when added-line coverage is below 80%', async () => {
        const lowCoverageData = {
            files: {
                [COVERAGE_KEY]: {
                    executed_lines: [1],
                    missing_lines: [2, 3] // 1/3 ≈ 33%
                }
            }
        };
        mockExistsSync
            .mockReturnValueOnce(true)
            .mockReturnValueOnce(false)
            .mockReturnValueOnce(true);
        setupTestFileFound();
        mockExecFileWith(null);
        mockReadFileSync.mockReturnValue(JSON.stringify(lowCoverageData));

        const result = await backendCoverageGuardrail.run(makeCtx([BACKEND_FILE]));

        expect(result.status).toBe('fail');
        expect(result.summary).toContain('[FAIL]');
        expect(result.summary).toContain(BACKEND_FILE.path);
    });

    it('auto-passes when pytest produces no entry for the source file', async () => {
        const unrelatedCoverageData = {
            files: {
                'src/lightly_studio/other.py': {
                    executed_lines: [1],
                    missing_lines: []
                }
            }
        };
        mockExistsSync
            .mockReturnValueOnce(true)
            .mockReturnValueOnce(false)
            .mockReturnValueOnce(true);
        setupTestFileFound();
        mockExecFileWith(null);
        mockReadFileSync.mockReturnValue(JSON.stringify(unrelatedCoverageData));

        const result = await backendCoverageGuardrail.run(makeCtx([BACKEND_FILE]));

        expect(result.status).toBe('pass');
    });

    it('fails when no test file is found for a changed source file', async () => {
        mockExistsSync.mockReturnValueOnce(true); // testsDir exists
        mockReaddir.mockResolvedValue([]); // no matching test files

        const result = await backendCoverageGuardrail.run(makeCtx([BACKEND_FILE]));

        expect(result.status).toBe('fail');
        expect(result.summary).toContain('no test file found');
        expect(result.summary).toContain(BACKEND_FILE.path);
    });

    it('passes immediately when no backend source files changed', async () => {
        const result = await backendCoverageGuardrail.run(
            makeCtx([
                {
                    path: 'lightly_studio_view/src/lib/foo.ts',
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
});
