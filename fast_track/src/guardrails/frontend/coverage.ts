import { execFile } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { promisify } from 'node:util';
import type { ChangedFile, Guardrail } from '../context/types';
import { FRONTEND_ABS, FRONTEND_PREFIX } from './eslint-runner';
import { createCoverageGuardrail } from '../shared/coverage-base';

const execFileAsync = promisify(execFile);
const SRC_PREFIX = FRONTEND_PREFIX + 'src/';

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

export const frontendCoverageGuardrail: Guardrail = createCoverageGuardrail<RawCoverage>({
    name: 'frontend/coverage',

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
            await execFileAsync(
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
