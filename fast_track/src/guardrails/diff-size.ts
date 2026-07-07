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
    'lightly_studio/uv.lock',
    'lightly_studio_view/package-lock.json',
    'fast_track/package-lock.json',
    'lightly_studio/tests/benchmarks/',
    'lightly_studio/src/lightly_studio/vendor/'
];

export function isExcluded(path: string): boolean {
    return EXCLUDED.some((e) => (e.endsWith('/') ? path.startsWith(e) : path === e));
}

export const diffSizeGuardrail: Guardrail = {
    name: NAME,
    required: true,
    needsPrContext: false,
    async run(ctx: GuardrailContext): Promise<GuardrailOutcome> {
        const files = await ctx.changedFiles();
        const totalAdditions = files
            .filter((f) => !isExcluded(f.path))
            .reduce((sum, f) => sum + f.additions, 0);

        if (totalAdditions > MAX_ADDED_LOC) {
            return {
                status: 'fail',
                summary: `PR adds ${totalAdditions} line(s), which exceeds the limit of ${MAX_ADDED_LOC}.`
            };
        }

        return {
            status: 'pass',
            summary: `PR adds ${totalAdditions} line(s) (limit: ${MAX_ADDED_LOC}).`
        };
    }
};
