import { describe, expect, it } from 'vitest';
import { filterBackendFiles, matchesTestFile, parseCoverageRatio } from './coverage';
import type { ChangedFile } from '../context/types';

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
