import type { Guardrail, GuardrailContext, GuardrailOutcome } from './context/types';

const NAME = 'diff-size';
// Hard cap of 200 added lines plus a 15-line buffer for minor overruns (e.g. boilerplate).
export const MAX_ADDED_LOC = 215;

/**
 * Paths and directory prefixes mirroring the linguist-generated / linguist-vendored
 * entries in .gitattributes. The GitHub API counts lines in these files even though
 * they are auto-generated, so we exclude them before comparing against the limit.
 * Directory prefixes end with '/' and match any file underneath them.
 */
const EXCLUDED: string[] = [
    'uv.lock',
    'lightly_studio_view/package-lock.json',
    'fast_track/package-lock.json',
    'lightly_studio/tests/benchmarks/',
    'lightly_studio/src/lightly_studio/vendor/'
];

/** Test code does not count against the limit: it is faster to review than source code. */
const TEST_FILE_PATTERNS: RegExp[] = [
    /(^|\/)tests\//,
    /^lightly_studio_view\/e2e\//,
    /^lightly_studio\/e2e-tests\//,
    /\.(test|spec)\.[^/]+$/,
    /(^|\/)test_[^/]*\.py$/,
    /_test\.py$/,
    /(^|\/)conftest\.py$/
];

export function isExcluded(path: string): boolean {
    return EXCLUDED.some((e) => (e.endsWith('/') ? path.startsWith(e) : path === e));
}

export function isTestFile(path: string): boolean {
    return TEST_FILE_PATTERNS.some((pattern) => pattern.test(path));
}

function countsTowardLimit(path: string): boolean {
    return !isExcluded(path) && !isTestFile(path);
}

export const diffSizeGuardrail: Guardrail = {
    name: NAME,
    required: true,
    async run(ctx: GuardrailContext): Promise<GuardrailOutcome> {
        const files = await ctx.changedFiles();
        const totalAdditions = files
            .filter((f) => countsTowardLimit(f.path))
            .reduce((sum, f) => sum + f.additions, 0);

        if (totalAdditions > MAX_ADDED_LOC) {
            return {
                status: 'fail',
                summary: `PR adds ${totalAdditions} non-test line(s), which exceeds the limit of ${MAX_ADDED_LOC}.`
            };
        }

        return {
            status: 'pass',
            summary: `PR adds ${totalAdditions} non-test line(s) (limit: ${MAX_ADDED_LOC}).`
        };
    }
};
