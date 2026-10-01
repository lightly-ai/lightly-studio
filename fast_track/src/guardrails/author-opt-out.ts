import type { Verdict, VerdictRouting } from '../shared/verdict';

export const OPT_OUT_LABEL = 'no-fast-track';

/** Return an override verdict when the PR author requested human review. */
export function buildOptOutVerdict(labels: string[], routing: VerdictRouting): Verdict | undefined {
    if (!labels.includes(OPT_OUT_LABEL)) return undefined;
    return {
        verdict: 'opt_out',
        guardrails: [],
        pr_number: routing.prNumber,
        head_sha: routing.headSha,
        base_ref: routing.baseRef,
        base_sha: routing.baseSha,
        reason: `Author requested human review with the \`${OPT_OUT_LABEL}\` label.`
    };
}
