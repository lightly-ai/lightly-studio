import { readdir } from 'node:fs/promises';
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { basename, relative, resolve } from 'node:path';
import type { ChangedFile, Guardrail } from '../context/types';
import { REPO_ROOT } from './shared';
import { createCoverageGuardrail } from '../shared/coverage-base';
import { runLoggedCommand } from '../shared/utils';

const LIGHTLY_STUDIO_ABS = resolve(REPO_ROOT, 'lightly_studio');
const NAME = 'backend/coverage';
// conftest.py imports the full app, whose webapp route raises at import time unless the
// built frontend dir exists. We don't build the frontend here, so mock it (an empty dir
// plus index.html satisfies both checks) — same approach as the Makefile's mock-webapp-dist.
const WEBAPP_DIST_DIR = resolve(
    LIGHTLY_STUDIO_ABS,
    'src/lightly_studio/dist_lightly_studio_view_app'
);
const BACKEND_PREFIX = 'lightly_studio/src/lightly_studio/';
const COVERAGE_FILE = 'coverage.json';
const MAX_BUFFER = 10 * 1024 * 1024;

interface CoverageFileData {
    executed_lines: number[];
    missing_lines: number[];
}

interface CoverageData {
    files: Record<string, CoverageFileData>;
}

export function filterBackendFiles(files: ChangedFile[]): ChangedFile[] {
    return files.filter(
        (f) => f.path.startsWith(BACKEND_PREFIX) && f.path.endsWith('.py') && !isExcluded(f.path)
    );
}

// Returns coverage ratio (0–1) for added lines only, or null if no added lines
// are executable (auto-pass). Uses coverage.py's per-line executed/missing arrays.
export function parseCoverageRatio(
    data: CoverageData,
    sourcePath: string,
    addedLines: Set<number>
): number | null {
    // coverage.json keys are relative to lightly_studio/; strip the prefix.
    const key = sourcePath.slice('lightly_studio/'.length);
    const entry = data.files[key];
    if (!entry) return null;

    const executableAdded = [...entry.executed_lines, ...entry.missing_lines].filter((line) =>
        addedLines.has(line)
    );
    if (executableAdded.length === 0) return null;

    const coveredAdded = entry.executed_lines.filter((line) => addedLines.has(line));
    return coveredAdded.length / executableAdded.length;
}

export const backendCoverageGuardrail: Guardrail = createCoverageGuardrail<CoverageData>({
    name: NAME,

    filterFiles(files: ChangedFile[]): ChangedFile[] {
        return filterBackendFiles(files);
    },

    async findTestFile(sourcePath: string): Promise<string | undefined> {
        const sourceName = basename(sourcePath, '.py');
        const testsDir = resolve(LIGHTLY_STUDIO_ABS, 'tests');
        if (!existsSync(testsDir)) return undefined;

        const prefix = `test_${sourceName}`;
        const entries = await readdir(testsDir, { recursive: true, withFileTypes: true });
        const candidates: string[] = [];

        for (const entry of entries) {
            if (!entry.isFile() || !matchesTestFile(entry.name, prefix)) continue;
            const fullPath = resolve(entry.parentPath, entry.name);
            candidates.push(relative(REPO_ROOT, fullPath));
        }

        if (candidates.length === 0) return undefined;
        if (candidates.length === 1) return candidates[0];

        return candidates.reduce((best, c) =>
            subpathOverlap(sourcePath, c) >= subpathOverlap(sourcePath, best) ? c : best
        );
    },

    // Runs a single pytest invocation covering all given test files and source paths.
    // testFiles and sourcePaths are repo-relative; deduplication of testFiles is the
    // caller's responsibility.
    async runTests(testFiles: string[], sourcePaths: string[]): Promise<CoverageData | null> {
        ensureWebappDist();
        // Pytest runs from lightly_studio/ so strip the leading lightly_studio/ prefix.
        const testFilesLocal = testFiles.map((f) => f.slice('lightly_studio/'.length));
        // coverage.py misreads *.py paths (relative or absolute) as module identifiers
        // and produces no data. Directory paths are matched by filesystem path instead,
        // so we pass the parent directory of each changed source file.
        // Deduplicate: multiple files in the same directory share one --cov arg.
        const covDirs = [
            ...new Set(
                sourcePaths.map((p) => {
                    const rel = p.slice('lightly_studio/'.length);
                    return rel.substring(0, rel.lastIndexOf('/'));
                })
            )
        ];
        const covArgs = covDirs.map((d) => `--cov=${d}`);
        const coveragePath = resolve(LIGHTLY_STUDIO_ABS, COVERAGE_FILE);

        // Remove any stale report so we only ever parse the file produced by this run.
        if (existsSync(coveragePath)) rmSync(coveragePath);

        try {
            await runLoggedCommand(
                NAME,
                'uv',
                [
                    'run',
                    'pytest',
                    ...testFilesLocal,
                    ...covArgs,
                    `--cov-report=json:${COVERAGE_FILE}`,
                    '-q',
                    '--no-header'
                ],
                { cwd: LIGHTLY_STUDIO_ABS, maxBuffer: MAX_BUFFER }
            );
        } catch (err: unknown) {
            // pytest exits non-zero when tests fail; coverage.json is still produced.
            // Re-throw for system-level errors (e.g. uv not on PATH, bad cwd).
            if (!existsSync(coveragePath)) throw err;
        }

        if (!existsSync(coveragePath)) return null;
        return JSON.parse(readFileSync(coveragePath, 'utf-8')) as CoverageData;
    },

    parseCoverageRatio(
        data: CoverageData,
        sourcePath: string,
        addedLines: Set<number>
    ): number | null {
        return parseCoverageRatio(data, sourcePath, addedLines);
    }
});

// Ensures the mocked webapp dist exists so importing the app in conftest.py doesn't raise.
// Idempotent; never overwrites an existing index.html (e.g. a real build on a dev machine).
export function ensureWebappDist(): void {
    mkdirSync(WEBAPP_DIST_DIR, { recursive: true });
    const indexFile = resolve(WEBAPP_DIST_DIR, 'index.html');
    if (!existsSync(indexFile)) writeFileSync(indexFile, '');
}

function isExcluded(path: string): boolean {
    const name = path.split('/').at(-1) ?? '';
    return (
        path.includes('/migrations/') ||
        (name.startsWith('test_') && name.endsWith('.py')) ||
        name === 'conftest.py' ||
        name === '__init__.py'
    );
}

// Matches test_<sourceName>.py and variants like test_<sourceName>_foo.py or test_<sourceName>__bar.py.
export function matchesTestFile(name: string, prefix: string): boolean {
    if (!name.startsWith(prefix) || !name.endsWith('.py')) return false;
    const afterPrefix = name.slice(prefix.length);
    return afterPrefix === '.py' || afterPrefix.startsWith('_');
}

function subpathOverlap(sourcePath: string, testPath: string): number {
    const sourceDirs = sourcePath.split('/').slice(0, -1).reverse();
    const testDirs = testPath.split('/').slice(0, -1).reverse();
    let count = 0;
    for (let i = 0; i < Math.min(sourceDirs.length, testDirs.length); i++) {
        if (sourceDirs[i] === testDirs[i]) count++;
        else break;
    }
    return count;
}
