import type { GuardrailResult, Verdict } from '../shared/verdict';
import type { RunResult } from './run-guardrails';

/** UNTRUSTED: written in PR context, re-derived by the bot against the trusted commit (design §3). */
export interface VerdictRouting {
    prNumber: number;
    headSha: string;
}

/**
 * Wrap a {@link RunResult} into the wire {@link Verdict}, adding the routing
 * fields and a {@link reason} for the PR comment on a non-pass. `opt_out` is
 * never produced here — it's an author-label override the bot applies (design §2.3).
 */
export function buildVerdict(run: RunResult, routing: VerdictRouting): Verdict {
    const verdict: Verdict = {
        verdict: run.status,
        guardrails: run.guardrails,
        pr_number: routing.prNumber,
        head_sha: routing.headSha
    };
    if (run.status !== 'pass') {
        verdict.reason = buildReason(run.guardrails);
    }
    return verdict;
}

function buildReason(guardrails: GuardrailResult[]): string {
    const failed = guardrails.filter((g) => g.status === 'fail');
    // A `fail` implies a failing guardrail, but never emit an empty reason if not.
    if (failed.length === 0) return 'One or more required guardrails did not pass.';
    return `Failed guardrails: ${failed.map((g) => `${g.name} (${g.summary})`).join(', ')}`;
}
