import type { RunResult } from '../guardrails/run-guardrails';
import type { Verdict } from '../shared/verdict';

/**
 * Untrusted routing anchors written into the verdict. The Bot re-derives these
 * from the trusted event and cross-checks them (design §2.2, §3) — Checks writes
 * them only so a missing artifact and a routed one look the same on the wire.
 */
export interface VerdictRouting {
    pr_number: number;
    head_sha: string;
}

/**
 * Wrap a {@link RunResult} into the on-the-wire {@link Verdict}: the run's
 * status becomes the overall verdict, the per-guardrail breakdown carries over
 * verbatim, and the routing anchors are attached. A non-pass run gets a
 * human-readable `reason` for the PR status comment.
 *
 * `opt_out` is not produced here — it is an author-label override the Bot
 * applies, never a guardrail-run outcome.
 */
export function buildVerdict(run: RunResult, routing: VerdictRouting): Verdict {
    const verdict: Verdict = {
        verdict: run.status,
        guardrails: run.guardrails,
        pr_number: routing.pr_number,
        head_sha: routing.head_sha
    };
    const reason = failureReason(run);
    if (reason !== undefined) {
        verdict.reason = reason;
    }
    return verdict;
}

/** A summary of the failing guardrails, or undefined when the run passed. */
function failureReason(run: RunResult): string | undefined {
    if (run.status === 'pass') return undefined;
    const failed = run.guardrails.filter((g) => g.status === 'fail').map((g) => g.name);
    return `Failed guardrail(s): ${failed.join(', ')}`;
}
