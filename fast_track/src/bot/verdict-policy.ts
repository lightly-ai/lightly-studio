import { OPT_OUT_LABEL } from '../guardrails/author-opt-out';
import type { Verdict } from '../shared/verdict';
import type { BotTarget } from './derive-target';
import { isVerdict } from './verdict-schema';

/** The subset of run inputs the verdict decision depends on. */
export interface VerdictInput {
    guardrailsSucceeded: boolean;
    requiredGuardrailNames: readonly string[];
    verdict: unknown;
}

/** Resolve the outcome to apply: the artifact verdict when trustworthy, else a
 *  synthesized opt-out/failure. Fail-closed — unexpected input never passes. */
export function effectiveVerdict(input: VerdictInput, target: BotTarget): Verdict {
    const { verdict, guardrailsSucceeded, requiredGuardrailNames } = input;

    if (target.labels.includes(OPT_OUT_LABEL)) {
        const reason = `Human review requested with the \`${OPT_OUT_LABEL}\` label.`;
        return failureVerdict('opt_out', target, reason);
    }
    if (!guardrailsSucceeded) {
        return failureVerdict(
            'fail',
            target,
            'The guardrail workflow did not complete successfully.'
        );
    }
    if (!isVerdict(verdict)) {
        return failureVerdict(
            'fail',
            target,
            'The guardrail workflow produced an invalid verdict.'
        );
    }
    if (verdict.verdict === 'pass' && !hasRequiredPasses(verdict, requiredGuardrailNames)) {
        return failureVerdict('fail', target, 'A required guardrail did not pass.');
    }
    if (!verdictMatchesTarget(verdict, target)) {
        return failureVerdict('fail', target, 'The guardrail verdict no longer matches this PR.');
    }
    return verdict;
}

/** Whether the verdict is still bound to the current PR target and not opted out. */
export function verdictMatchesTarget(verdict: Verdict, target: BotTarget): boolean {
    return (
        verdict.pr_number === target.prNumber &&
        verdict.head_sha === target.headSha &&
        verdict.base_ref === target.baseRef &&
        verdict.base_sha === target.baseSha &&
        !target.labels.includes(OPT_OUT_LABEL)
    );
}

function failureVerdict(status: 'fail' | 'opt_out', target: BotTarget, reason: string): Verdict {
    return {
        verdict: status,
        guardrails: [],
        pr_number: target.prNumber,
        head_sha: target.headSha,
        base_ref: target.baseRef,
        base_sha: target.baseSha,
        reason
    };
}

/** Policy check: every required guardrail is present and passing. Fail-closed —
 *  an empty required set is treated as missing configuration, never as a pass. */
function hasRequiredPasses(verdict: Verdict, requiredGuardrailNames: readonly string[]): boolean {
    return (
        requiredGuardrailNames.length > 0 &&
        requiredGuardrailNames.every((name) =>
            verdict.guardrails.some(
                (guardrail) => guardrail.name === name && guardrail.status === 'pass'
            )
        )
    );
}
