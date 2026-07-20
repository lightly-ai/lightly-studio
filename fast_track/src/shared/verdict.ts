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
    /** Untrusted routing: binds the verdict to the base branch used for judging. */
    base_ref: string;
    /** Untrusted routing: binds the verdict to the exact base revision used for judging. */
    base_sha: string;
    /** Shown in the PR comment on a non-pass verdict. */
    reason?: string;
}

/**
 * The camelCase routing inputs the verdict builders map onto the snake_case wire
 * fields above. Shared by every builder, so it lives here rather than being owned
 * by one builder module. UNTRUSTED: written in PR context, re-derived by the Bot
 * against the trusted commit (design §3).
 */
export interface VerdictRouting {
    prNumber: number;
    headSha: string;
    baseRef: string;
    baseSha: string;
}
