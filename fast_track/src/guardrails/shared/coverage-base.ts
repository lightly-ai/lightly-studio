import { extractAddedLines, pct } from './utils';
import type { ChangedFile, Guardrail, GuardrailContext } from '../context/types';
import type { GuardrailOutcome } from '../context/types';

const MIN_COVERAGE = 0.8;
const MIN_COVERAGE_PCT = `${(MIN_COVERAGE * 100).toFixed(0)}%`;

export interface CoverageConfig<TCoverage> {
    name: string;
    filterFiles(files: ChangedFile[]): ChangedFile[];
    findTestFile(sourcePath: string): Promise<string | undefined>;
    runTests(testFiles: string[], sourcePaths: string[]): Promise<TCoverage | null>;
    parseCoverageRatio(data: TCoverage, sourcePath: string, addedLines: Set<number>): number | null;
}

type Pair = { source: ChangedFile; testFile: string };

function buildAddedLinesMap(files: ChangedFile[]): Map<string, Set<number>> {
    const map = new Map<string, Set<number>>();
    for (const f of files) {
        if (f.patch !== undefined) {
            map.set(f.path, extractAddedLines(f.patch));
        }
    }
    return map;
}

async function resolvePairs(
    sourceFiles: ChangedFile[],
    findTestFile: (path: string) => Promise<string | undefined>
): Promise<{ pairs: Pair[]; failures: string[] }> {
    const pairs: Pair[] = [];
    const failures: string[] = [];
    for (const file of sourceFiles) {
        const testFile = await findTestFile(file.path);
        if (!testFile) {
            failures.push(`${file.path}: no test file found`);
        } else {
            pairs.push({ source: file, testFile });
        }
    }
    return { pairs, failures };
}

async function runCoverage<TCoverage>(
    pairs: Pair[],
    runTests: (testFiles: string[], sourcePaths: string[]) => Promise<TCoverage | null>
): Promise<TCoverage | null> {
    if (pairs.length === 0) return null;
    const testFiles = [...new Set(pairs.map((p) => p.testFile))];
    const sourcePaths = pairs.map((p) => p.source.path);
    return runTests(testFiles, sourcePaths);
}

function collectCoverageResults<TCoverage>(
    pairs: Pair[],
    coverageData: TCoverage | null,
    addedLinesByFile: Map<string, Set<number>>,
    parseCoverageRatio: (
        data: TCoverage,
        sourcePath: string,
        addedLines: Set<number>
    ) => number | null
): { lines: string[]; failures: string[]; checked: number } {
    const failures: string[] = [];
    const lines: string[] = [];
    let checked = 0;
    for (const { source } of pairs) {
        // Files without a patch cannot be line-filtered; skip them.
        const addedLines = addedLinesByFile.get(source.path);
        if (addedLines === undefined) continue;
        if (coverageData === null) {
            const msg = `${source.path}: coverage data not found`;
            failures.push(msg);
            lines.push(`  [FAIL] ${msg}`);
            continue;
        }
        const ratio = parseCoverageRatio(coverageData, source.path, addedLines);
        checked++;
        if (ratio === null) continue; // no added executable lines → pass
        if (ratio < MIN_COVERAGE) {
            const msg = `${source.path}: ${pct(ratio)} coverage (required ${MIN_COVERAGE_PCT})`;
            failures.push(msg);
            lines.push(`  [FAIL] ${msg}`);
        } else {
            lines.push(`  [PASS] ${source.path}: ${pct(ratio)}`);
        }
    }
    return { lines, failures, checked };
}

export function createCoverageGuardrail<TCoverage>(config: CoverageConfig<TCoverage>): Guardrail {
    return {
        name: config.name,
        required: true,
        needsPrContext: false,

        async run(ctx: GuardrailContext): Promise<GuardrailOutcome> {
            const files = await ctx.changedFiles();
            const sourceFiles = config
                .filterFiles(files)
                .filter((f) => f.status !== 'deleted' && f.patch !== undefined);

            if (sourceFiles.length === 0) {
                return { status: 'pass', summary: '0 file(s) checked.' };
            }

            const addedLinesByFile = buildAddedLinesMap(sourceFiles);
            const checkableFiles = sourceFiles.filter((f) => {
                const lines = addedLinesByFile.get(f.path);
                return lines !== undefined && lines.size > 0;
            });

            if (checkableFiles.length === 0) {
                return { status: 'pass', summary: '0 file(s) checked.' };
            }

            const { pairs, failures: pairFailures } = await resolvePairs(
                checkableFiles,
                config.findTestFile
            );
            const coverageData = await runCoverage(pairs, config.runTests);
            const {
                lines,
                failures: coverageFailures,
                checked
            } = collectCoverageResults(
                pairs,
                coverageData,
                addedLinesByFile,
                config.parseCoverageRatio
            );

            const failures = [...pairFailures, ...coverageFailures];
            const allLines = [...pairFailures.map((f) => `  [FAIL] ${f}`), ...lines];

            if (failures.length === 0) {
                const summary =
                    allLines.length > 0
                        ? allLines.join('\n')
                        : `${checked} file(s) checked, all above ${MIN_COVERAGE_PCT}.`;
                return { status: 'pass', summary };
            }

            return { status: 'fail', summary: allLines.join('\n') };
        }
    };
}
