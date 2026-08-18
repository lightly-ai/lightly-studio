import type { ChangedFile, Guardrail } from '../context/types';
import { createCoverageGuardrail, type LineCoverage } from '../shared/full-suite-coverage';
import { BACKEND_PREFIX } from './shared';

const BACKEND_SRC_PREFIX = BACKEND_PREFIX + 'src/lightly_studio/';

export interface CoverageFileData {
    executed_lines: number[];
    missing_lines: number[];
}

interface CoverageData {
    files: Record<string, CoverageFileData>;
}

export function filterBackendFiles(files: ChangedFile[]): ChangedFile[] {
    return files.filter(
        (f) =>
            f.path.startsWith(BACKEND_SRC_PREFIX) &&
            f.path.endsWith('.py') &&
            !isExcludedBackendPath(f.path)
    );
}

/** Normalises a coverage.py JSON report into repo-relative per-line coverage. */
export function parseBackendReport(raw: string): LineCoverage {
    const data = JSON.parse(raw) as CoverageData;
    const coverage: LineCoverage = new Map();
    for (const [key, entry] of Object.entries(data.files)) {
        // coverage.py writes keys relative to the directory pytest ran in.
        coverage.set(BACKEND_PREFIX + key, {
            executable: new Set([...entry.executed_lines, ...entry.missing_lines]),
            covered: new Set(entry.executed_lines)
        });
    }
    return coverage;
}

export const backendCoverageGuardrail: Guardrail = createCoverageGuardrail({
    name: 'backend/coverage',
    coverageJsonEnvVar: 'BACKEND_COVERAGE_JSON',
    testsPassedEnvVar: 'BACKEND_TESTS_PASSED',
    filterFiles: filterBackendFiles,
    parseReport: parseBackendReport
});

// `examples/` has no `__init__.py`, so coverage.py's source scan never reaches it.
// `vendor/` is third-party code we do not hold to a coverage bar.
const EXCLUDED_DIRS = ['migrations', 'examples', 'vendor'];

function isExcludedBackendPath(path: string): boolean {
    const name = path.split('/').at(-1) ?? '';
    return (
        EXCLUDED_DIRS.some((dir) => path.includes(`/${dir}/`)) ||
        (name.startsWith('test_') && name.endsWith('.py')) ||
        name === 'conftest.py' ||
        name === '__init__.py'
    );
}
