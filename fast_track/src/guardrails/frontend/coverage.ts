import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import type { ChangedFile, Guardrail } from '../context/types';
import { FRONTEND_ABS, FRONTEND_PREFIX } from './eslint-runner';
import { createCoverageGuardrail } from '../shared/coverage-base';
import type { FileLineCoverage, LineCoverage } from '../shared/full-suite-coverage';
import { runLoggedCommand } from '../shared/utils';

const SRC_PREFIX = FRONTEND_PREFIX + 'src/';

const NAME = 'frontend/coverage';
const IGNORE_SUFFIXES = ['.test.ts', '.test.js', '.spec.ts', '.spec.js', '.d.ts'];
const SOURCE_SUFFIXES = ['.ts', '.js', '.svelte'];
const MAX_BUFFER = 32 * 1024 * 1024;
const COVERAGE_JSON = 'coverage/coverage-final.json';

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

// Map a source file (repo-relative) to its test file (relative to FRONTEND_ABS),
// using the project's *.test.ts / *.spec.ts naming convention.
function findFrontendTestFile(repoRelative: string): string | undefined {
    const relToFrontend = repoRelative.slice(FRONTEND_PREFIX.length); // src/lib/foo.ts
    let withoutExt = relToFrontend.replace(/\.(ts|js|svelte)$/, '');
    // Strip .svelte suffix from rune module stems (foo.svelte.ts → foo)
    withoutExt = withoutExt.replace(/\.svelte$/, '');
    // Strip SvelteKit + prefix from basename (+page → page)
    withoutExt = withoutExt.replace(/(^|\/)\+/, '$1');
    const candidates = [
        `${withoutExt}.test.ts`,
        `${withoutExt}.test.js`,
        `${withoutExt}.spec.ts`,
        `${withoutExt}.spec.js`
    ];
    return candidates.find((c) => existsSync(resolve(FRONTEND_ABS, c)));
}

// Returns coverage ratio (0–1) for added lines only. A statement contributes one
// count per source line (start.line..end.line) that appears in addedLines.
// Returns null when no added lines map to executable statements (auto-pass).
export function fileCoverageRatio(
    entry: IstanbulFileCoverage,
    addedLines: Set<number>
): number | null {
    let executable = 0;
    let covered = 0;
    for (const [idx, loc] of Object.entries(entry.statementMap)) {
        for (let line = loc.start.line; line <= loc.end.line; line++) {
            if (!addedLines.has(line)) continue;
            executable++;
            if ((entry.s[idx] ?? 0) > 0) covered++;
        }
    }
    return executable === 0 ? null : covered / executable;
}

/**
 * Normalises a vitest (Istanbul/v8) coverage report into repo-relative per-line
 * coverage. Each statement is collapsed to the lines it spans: a line is
 * `executable` if any statement covers it, `covered` if any covering statement
 * has a hit count > 0.
 */
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

export const frontendCoverageGuardrail: Guardrail = createCoverageGuardrail<RawCoverage>({
    name: NAME,

    filterFiles(files: ChangedFile[]): ChangedFile[] {
        return files.filter(
            (f) =>
                f.path.startsWith(SRC_PREFIX) &&
                SOURCE_SUFFIXES.some((s) => f.path.endsWith(s)) &&
                !IGNORE_SUFFIXES.some((s) => f.path.endsWith(s))
        );
    },

    findTestFile(sourcePath: string): Promise<string | undefined> {
        return Promise.resolve(findFrontendTestFile(sourcePath));
    },

    async runTests(testFiles: string[], sourcePaths: string[]): Promise<RawCoverage | null> {
        const relSources = sourcePaths.map((p) => p.slice(FRONTEND_PREFIX.length));
        const coverageIncludes = relSources.map((f) => `--coverage.include=${f}`);
        try {
            await runLoggedCommand(
                NAME,
                'npm',
                ['run', 'test:unit', '--', 'run', '--coverage', ...testFiles, ...coverageIncludes],
                { cwd: FRONTEND_ABS, maxBuffer: MAX_BUFFER }
            );
        } catch (err) {
            // vitest exits non-zero when tests fail; coverage file is still produced.
            // Re-throw system-level errors (e.g. npm not on PATH, cwd not found):
            // those have a string code (e.g. 'ENOENT'), whereas non-zero exits have a numeric code.
            if (typeof (err as NodeJS.ErrnoException).code === 'string') {
                throw err;
            }
        }
        const coveragePath = resolve(FRONTEND_ABS, COVERAGE_JSON);
        if (!existsSync(coveragePath)) return null;
        return JSON.parse(readFileSync(coveragePath, 'utf-8')) as RawCoverage;
    },

    parseCoverageRatio(
        data: RawCoverage,
        sourcePath: string,
        addedLines: Set<number>
    ): number | null {
        // Istanbul keys are absolute paths; resolve the entry by matching the repo-relative suffix.
        let entry: IstanbulFileCoverage | undefined;
        for (const [absPath, e] of Object.entries(data)) {
            const idx = absPath.indexOf(FRONTEND_PREFIX);
            if (idx !== -1 && absPath.slice(idx) === sourcePath) {
                entry = e;
                break;
            }
        }
        if (!entry) return null;
        return fileCoverageRatio(entry, addedLines);
    }
});
