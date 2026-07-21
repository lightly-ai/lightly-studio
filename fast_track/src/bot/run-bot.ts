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

/** Apply a current pass verdict, revoking the bot approval for every other outcome. */
export async function runBot(params: RunBotParams): Promise<BotResult> {
    const target = await currentTarget(params);
    if (target === null) {
        return { status: 'skipped', reason: 'No eligible PR matched the trusted workflow run.' };
    }

    const verdict = effectiveVerdict(params, target);
    const actionParams: BotActionParams = {
        octokit: params.octokit,
        owner: params.owner,
        repo: params.repo,
        prNumber: target.prNumber,
        botLogin: params.botLogin
    };
    return verdict.verdict === 'pass'
        ? applyPass(params, target, verdict, actionParams)
        : applyFailure(target, verdict, actionParams);
}

async function currentTarget(params: RunBotParams): Promise<BotTarget | null> {
    const derivedTarget = await deriveTarget(params);
    if (derivedTarget === null) return null;
    return refreshTarget({ ...params, target: derivedTarget });
}

/**
 * Reload the target, treating a failed reload as "no longer verifiable" so the
 * caller fails closed. A throw here would otherwise skip the post-approval
 * rollback and leave an unverified approval active.
 */
async function refreshOrNull(
    params: Parameters<typeof refreshTarget>[0]
): Promise<BotTarget | null> {
    try {
        return await refreshTarget(params);
    } catch (error) {
        console.warn(
            'Fast Track: target refresh failed; treating the target as unverifiable.',
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
    const finalTarget = await refreshOrNull({ ...params, target });
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
