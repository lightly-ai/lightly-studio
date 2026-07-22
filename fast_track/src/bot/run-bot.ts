import type { Octokit } from '../guardrails/context/types';
import type { Verdict } from '../shared/verdict';
import { renderComment, upsertComment } from './comment';
import { deriveTarget, refreshTarget, type BotTarget } from './derive-target';
import { approve, dismissApproval } from './review';
import { effectiveVerdict, verdictMatchesTarget } from './verdict-policy';

interface RunBotParams {
    octokit: Octokit;
    owner: string;
    repo: string;
    trustedHeadSha: string;
    botLogin: string;
    guardrailsSucceeded: boolean;
    requiredGuardrailNames: readonly string[];
    verdict: unknown;
}

export type BotResult =
    { status: 'approved' | 'dismissed'; prNumber: number } | { status: 'skipped'; reason: string };

type BotActionParams = Parameters<typeof dismissApproval>[0];

/** A verified target ready to act on, or the finished result to return when
 *  there is nothing to act on (no PR) or the target could not be verified. */
type VerifyOutcome = { target: BotTarget; actionParams: BotActionParams } | { done: BotResult };

/** Apply a current pass verdict, revoking the bot approval for every other outcome. */
export async function runBot(params: RunBotParams): Promise<BotResult> {
    const outcome = await verifyTarget(params);
    if ('done' in outcome) return outcome.done;

    const { target, actionParams } = outcome;
    const verdict = effectiveVerdict(params, target);
    return verdict.verdict === 'pass'
        ? applyPass(params, target, verdict, actionParams)
        : applyFailure(target, verdict, actionParams);
}

/**
 * Find the target and reload its mutable state before any write. If there is no
 * PR, skip. If the target is no longer verifiable, fail closed: dismiss any
 * existing approval bound to this PR rather than skip, which would leave a stale
 * approval active.
 */
async function verifyTarget(params: RunBotParams): Promise<VerifyOutcome> {
    const derivedTarget = await deriveTarget(params);
    if (derivedTarget === null) {
        return {
            done: { status: 'skipped', reason: 'No eligible PR matched the trusted workflow run.' }
        };
    }

    const actionParams = toActionParams(params, derivedTarget.prNumber);
    const target = await targetOrNull(() => refreshTarget({ ...params, target: derivedTarget }));
    if (target === null) {
        await dismissApproval(actionParams);
        return { done: { status: 'dismissed', prNumber: derivedTarget.prNumber } };
    }
    return { target, actionParams };
}

function toActionParams(params: RunBotParams, prNumber: number): BotActionParams {
    return {
        octokit: params.octokit,
        owner: params.owner,
        repo: params.repo,
        prNumber,
        botLogin: params.botLogin
    };
}

/**
 * Resolve a target, treating a thrown error as "no longer verifiable" so the
 * caller fails closed. A throw would otherwise skip the pre-approval dismissal
 * or the post-approval rollback and leave an unverified approval active.
 */
async function targetOrNull(resolve: () => Promise<BotTarget | null>): Promise<BotTarget | null> {
    try {
        return await resolve();
    } catch (error) {
        console.warn(
            'Fast Track: target check failed; treating the target as unverifiable.',
            error
        );
        return null;
    }
}

async function applyPass(
    params: RunBotParams,
    target: BotTarget,
    verdict: Verdict,
    actionParams: BotActionParams
): Promise<BotResult> {
    await approve({ ...actionParams, headSha: target.headSha });
    // Re-derive rather than reload: the re-check must re-run the "exactly one
    // eligible PR at this head" invariant, not just reload the single known PR.
    const finalTarget = await targetOrNull(() => deriveTarget(params));
    if (finalTarget === null || !verdictMatchesTarget(verdict, finalTarget)) {
        await dismissApproval(actionParams);
        return { status: 'dismissed', prNumber: target.prNumber };
    }

    await updateStatusComment(verdict, finalTarget.headSha, actionParams);
    return { status: 'approved', prNumber: finalTarget.prNumber };
}

async function applyFailure(
    target: BotTarget,
    verdict: Verdict,
    actionParams: BotActionParams
): Promise<BotResult> {
    await dismissApproval(actionParams);
    await updateStatusComment(verdict, target.headSha, actionParams);
    return { status: 'dismissed', prNumber: target.prNumber };
}

async function updateStatusComment(
    verdict: Verdict,
    headSha: string,
    params: Omit<Parameters<typeof upsertComment>[0], 'body'>
): Promise<void> {
    await upsertComment({ ...params, body: renderComment(verdict, headSha) });
}
