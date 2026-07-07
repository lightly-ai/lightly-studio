import type { Guardrail, GuardrailContext, GuardrailOutcome } from './context/types';

const NAME = 'diff-size';
export const MAX_ADDED_LOC = 215;

export const diffSizeGuardrail: Guardrail = {
    name: NAME,
    required: true,
    needsPrContext: false,
    async run(ctx: GuardrailContext): Promise<GuardrailOutcome> {
        const files = await ctx.changedFiles();
        const totalAdditions = files.reduce((sum, f) => sum + f.additions, 0);

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
