import { existsSync, readFileSync } from 'node:fs';
import { extractAddedLines, pct } from './utils';
import type { ChangedFile, Guardrail, GuardrailContext } from '../context/types';
import type { GuardrailOutcome } from '../context/types';

const MIN_COVERAGE = 0.9;
const MIN_COVERAGE_PCT = `${(MIN_COVERAGE * 100).toFixed(0)}%`;

export interface FileLineCoverage {
    /** Lines the coverage tool considers executable. */
    executable: Set<number>;
    /** Executable lines that were actually executed. */
    covered: Set<number>;
}

/** Per-file line coverage, keyed by repo-relative path. */
export type LineCoverage = Map<string, FileLineCoverage>;

export interface CoverageConfig {
    name: string;
    /** Env var holding the path to the report the workflow's test step produced. */
    coverageJsonEnvVar: string;
    /** Env var set to `false` when that test step ended red. */
    testsPassedEnvVar: string;
    filterFiles(files: ChangedFile[]): ChangedFile[];
    /** Normalises the raw report, mapping its keys to repo-relative paths. */
    parseReport(raw: string): LineCoverage;
}

/**
 * Builds a coverage guardrail that reads a **full-suite** coverage report the
 * workflow already produced; it never runs tests itself. Every changed source
 * file is judged on its own added lines, so one well-covered file cannot carry
 * an uncovered one.
 */
export function createCoverageGuardrail(config: CoverageConfig): Guardrail {
    return {
        name: config.name,
        required: true,
        needsPrContext: false,

        async run(ctx: GuardrailContext): Promise<GuardrailOutcome> {
            const files = await ctx.changedFiles();
            const scoped = filesInScope(config.filterFiles(files));
            if (scoped.length === 0) {
                return { status: 'pass', summary: '0 file(s) checked.' };
            }

            const lookup = loadReport(config);
            return 'report' in lookup ? judge(scoped, lookup.report) : lookup.outcome;
        }
    };
}

/** Either the parsed report, or the outcome that stands in for a missing one. */
type ReportLookup = { report: LineCoverage } | { outcome: GuardrailOutcome };

function loadReport(config: CoverageConfig): ReportLookup {
    const reportPath = process.env[config.coverageJsonEnvVar];
    if (reportPath === undefined || reportPath === '') {
        const summary = `coverage skipped: ${config.coverageJsonEnvVar} not set (no full-suite report available outside CI).`;
        return { outcome: { status: 'pass', summary } };
    }

    if (process.env[config.testsPassedEnvVar] === 'false') {
        const summary = 'test suite failed; coverage not evaluated on partial data.';
        return { outcome: { status: 'fail', summary } };
    }

    if (!existsSync(reportPath)) {
        return { outcome: { status: 'fail', summary: `coverage report missing: ${reportPath}` } };
    }

    return { report: config.parseReport(readFileSync(reportPath, 'utf-8')) };
}

/** A file a per-added-line ratio can be computed for. */
interface ScopedFile {
    path: string;
    addedLines: Set<number>;
}

function filesInScope(files: ChangedFile[]): ScopedFile[] {
    return files.flatMap((file) => {
        // Deleted files have no lines to cover; patch-less files (binary, or a
        // diff too large for the API) cannot be line-filtered.
        if (file.status === 'deleted' || file.patch === undefined) return [];
        const addedLines = extractAddedLines(file.patch);
        return addedLines.size > 0 ? [{ path: file.path, addedLines }] : [];
    });
}

interface FileVerdict {
    failed: boolean;
    line: string;
}

function judgeFile({ path, addedLines }: ScopedFile, report: LineCoverage): FileVerdict {
    const entry = report.get(path);
    if (entry === undefined) {
        return { failed: true, line: `  [FAIL] ${path}: not found in coverage report` };
    }

    const ratio = addedLineRatio(entry, addedLines);
    if (ratio === null) {
        return { failed: false, line: `  [PASS] ${path}: no executable added lines` };
    }
    if (ratio < MIN_COVERAGE) {
        const line = `  [FAIL] ${path}: ${pct(ratio)} coverage (required ${MIN_COVERAGE_PCT})`;
        return { failed: true, line };
    }
    return { failed: false, line: `  [PASS] ${path}: ${pct(ratio)}` };
}

function judge(scoped: ScopedFile[], report: LineCoverage): GuardrailOutcome {
    const verdicts = scoped.map((file) => judgeFile(file, report));
    const summary = [
        `${scoped.length} file(s) checked at ${MIN_COVERAGE_PCT}.`,
        ...verdicts.map((verdict) => verdict.line)
    ].join('\n');
    return { status: verdicts.some((verdict) => verdict.failed) ? 'fail' : 'pass', summary };
}

/** Coverage of the added lines only, or null when none of them is executable. */
function addedLineRatio(entry: FileLineCoverage, addedLines: Set<number>): number | null {
    let executable = 0;
    let covered = 0;
    for (const line of addedLines) {
        if (!entry.executable.has(line)) continue;
        executable++;
        if (entry.covered.has(line)) covered++;
    }
    return executable === 0 ? null : covered / executable;
}
