import type { ChangedFile, Guardrail } from '../context/types';
import {
    createCoverageGuardrail,
    type FileLineCoverage,
    type LineCoverage
} from '../shared/full-suite-coverage';
import { FRONTEND_PREFIX } from './shared';

const SRC_PREFIX = FRONTEND_PREFIX + 'src/';

const IGNORE_SUFFIXES = [
    '.test.ts',
    '.test.js',
    '.test.svelte',
    '.spec.ts',
    '.spec.js',
    '.spec.svelte',
    '.d.ts',
    '.stories.svelte',
    '.stories.ts',
    '.stories.js',
    'setupTests.ts'
];
const SOURCE_SUFFIXES = ['.ts', '.js', '.svelte'];

// Istanbul v8 coverage types (as written by @vitest/coverage-v8).
interface IstanbulLocation {
    line: number;
    column: number;
}
interface IstanbulStatement {
    start: IstanbulLocation;
    end: IstanbulLocation;
}
interface IstanbulFileCoverage {
    statementMap: Record<string, IstanbulStatement>;
    s: Record<string, number>;
}

type RawCoverage = Record<string, IstanbulFileCoverage>;

export function filterFrontendFiles(files: ChangedFile[]): ChangedFile[] {
    return files.filter(
        (f) =>
            f.path.startsWith(SRC_PREFIX) &&
            SOURCE_SUFFIXES.some((s) => f.path.endsWith(s)) &&
            !IGNORE_SUFFIXES.some((s) => f.path.endsWith(s))
    );
}

/** Reads a vitest (Istanbul/v8) report into per-line coverage, keyed by repo-relative path. */
export function parseFrontendReport(raw: string): LineCoverage {
    const data = JSON.parse(raw) as RawCoverage;
    const coverage: LineCoverage = new Map();
    for (const [rawPath, entry] of Object.entries(data)) {
        // Istanbul keys are absolute paths; map to the repo-relative suffix,
        // normalising Windows separators so the slash-based prefix still matches.
        const absPath = rawPath.replace(/\\/g, '/');
        const idx = absPath.indexOf(FRONTEND_PREFIX);
        if (idx === -1) continue;
        coverage.set(absPath.slice(idx), toFileLineCoverage(entry));
    }
    return coverage;
}

function toFileLineCoverage(entry: IstanbulFileCoverage): FileLineCoverage {
    const executable = new Set<number>();
    const covered = new Set<number>();
    for (const [idx, loc] of Object.entries(entry.statementMap)) {
        const hit = (entry.s[idx] ?? 0) > 0;
        for (let line = loc.start.line; line <= loc.end.line; line++) {
            executable.add(line);
            if (hit) covered.add(line);
        }
    }
    return { executable, covered };
}

export const frontendCoverageGuardrail: Guardrail = createCoverageGuardrail({
    name: 'frontend/coverage',
    coverageJsonEnvVar: 'FRONTEND_COVERAGE_JSON',
    testsPassedEnvVar: 'FRONTEND_TESTS_PASSED',
    filterFiles: filterFrontendFiles,
    parseReport: parseFrontendReport
});
