/**
 * The verdict contract between the Fast Track Guardrails and the Fast Track Bot:
 * the Guardrails serialize a {@link Verdict} to JSON, the Bot reads it back. This
 * JSON is the wire format, so field names are snake_case with no serialization layer.
 */

export type GuardrailStatus = 'pass' | 'fail';

/** `opt_out` is an author-label override, never a guardrail status. */
export type VerdictStatus = 'pass' | 'fail' | 'opt_out';

export interface GuardrailResult {
    name: string;
    status: GuardrailStatus;
    summary: string;
}

export interface Verdict {
    verdict: VerdictStatus;
    guardrails: GuardrailResult[];
    /** Untrusted routing: PR-context code writes it, the Bot re-derives and cross-checks. */
    pr_number: number;
    /** Untrusted routing: PR-context code writes it, the Bot re-derives and cross-checks. */
    head_sha: string;
    /** Shown in the PR comment on a non-pass verdict. */
    reason?: string;
}
