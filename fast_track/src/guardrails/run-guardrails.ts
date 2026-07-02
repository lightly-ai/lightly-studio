import type { GuardrailStatus, GuardrailResult } from '../shared/verdict';
import type { Guardrail, GuardrailContext } from './context/types';

export interface RunResult {
    /** `pass` iff every *required* guardrail passed. */
    status: GuardrailStatus;
    /** One entry per guardrail, in run order. */
    guardrails: GuardrailResult[];
}

/**
 * Run the guardrails sequentially and aggregate: `pass` iff every *required*
 * one passed. Pure over {@link GuardrailContext}, so CI and local runs share it.
 *
 * Guardrails run PR-author-controlled code, so results are normalized in
 * {@link runOne} (fail-closed on a throw or a non-`pass` status, name taken from
 * the definition), and required-ness is read from the guardrail definition.
 */
export async function runGuardrails(
    context: GuardrailContext,
    guardrails: Guardrail[]
): Promise<RunResult> {
    const results: GuardrailResult[] = [];
    let status: GuardrailStatus = 'pass';

    for (const guardrail of guardrails) {
        const result = await runOne(guardrail, context);
        results.push(result);
        if (guardrail.required && result.status === 'fail') {
            status = 'fail';
        }
    }

    return { status, guardrails: results };
}

/**
 * Run one guardrail into a well-formed result. The name always comes from the
 * definition so the breakdown can't be mislabeled, and the status fails closed:
 * a throw, or anything other than `pass`, becomes `fail`.
 */
async function runOne(guardrail: Guardrail, context: GuardrailContext): Promise<GuardrailResult> {
    try {
        const result = await guardrail.run(context);
        return {
            name: guardrail.name,
            status: result.status === 'pass' ? 'pass' : 'fail',
            summary: result.summary
        };
    } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        return {
            name: guardrail.name,
            status: 'fail',
            summary: `Guardrail threw: ${message}`
        };
    }
}
