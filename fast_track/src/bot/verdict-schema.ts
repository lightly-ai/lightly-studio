import type { GuardrailResult, Verdict } from '../shared/verdict';

/**
 * Structural guard for an untrusted JSON artifact. `opt_out` is intentionally rejected:
 * it is synthesized from the live PR label, never trusted from the artifact.
 */
export function isVerdict(value: unknown): value is Verdict {
    if (!isRecord(value)) return false;
    if (value.verdict !== 'pass' && value.verdict !== 'fail') return false;
    if (!Array.isArray(value.guardrails) || !value.guardrails.every(isGuardrailResult)) {
        return false;
    }
    const names = value.guardrails.map((guardrail) => guardrail.name);
    if (new Set(names).size !== names.length) return false;
    return (
        Number.isInteger(value.pr_number) &&
        typeof value.head_sha === 'string' &&
        typeof value.base_ref === 'string' &&
        typeof value.base_sha === 'string' &&
        (value.reason === undefined || typeof value.reason === 'string')
    );
}

function isGuardrailResult(value: unknown): value is GuardrailResult {
    if (!isRecord(value)) return false;
    return (
        typeof value.name === 'string' &&
        (value.status === 'pass' || value.status === 'fail') &&
        typeof value.summary === 'string'
    );
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}
