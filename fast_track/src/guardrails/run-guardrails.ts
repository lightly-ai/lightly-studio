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
 * Guardrails run PR-author-controlled code, so a throwing guardrail is recorded
 * as a `fail` rather than crashing the run (see {@link runOne}), and required-ness
 * is read from the guardrail definition.
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
 * Run one guardrail into a full result: the name from the definition (a
 * {@link GuardrailOutcome} carries none) plus its outcome, or a `fail` if it throws.
 */
async function runOne(guardrail: Guardrail, context: GuardrailContext): Promise<GuardrailResult> {
    try {
        const outcome = await guardrail.run(context);
        return { name: guardrail.name, ...outcome };
    } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        return {
            name: guardrail.name,
            status: 'fail',
            summary: `Guardrail threw: ${message}`
        };
    }
}
