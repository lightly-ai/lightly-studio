import type { Octokit } from '../guardrails/context/types';

/** `listPullRequestsAssociatedWithCommit` caps per_page at 100. */
const PER_PAGE = 100;

export interface BotTarget {
    prNumber: number;
    headSha: string;
    baseRef: string;
    baseSha: string;
    labels: string[];
}

interface DeriveTargetParams {
    octokit: Octokit;
    owner: string;
    repo: string;
    trustedHeadSha: string;
}

/**
 * Find the pull request that the workflow_run head SHA belongs to, using
 * GitHub as the source of truth. Returns the matching PR, or null when there
 * is no safe target: no open PR at that exact head SHA, a draft, a fork, or
 * more than one candidate.
 */
export async function deriveTarget(params: DeriveTargetParams): Promise<BotTarget | null> {
    const { octokit, owner, repo, trustedHeadSha } = params;
    // Walk every page: the "exactly one candidate" check below is a security
    // invariant, so it must see all associated PRs, not just the first page.
    const pullRequests = await octokit.paginate(
        octokit.rest.repos.listPullRequestsAssociatedWithCommit,
        { owner, repo, commit_sha: trustedHeadSha, per_page: PER_PAGE }
    );

    const eligiblePullRequests = pullRequests.filter(
        (candidate) =>
            candidate.state === 'open' &&
            !candidate.draft &&
            candidate.head.sha === trustedHeadSha &&
            !isFork(candidate)
    );
    if (eligiblePullRequests.length !== 1) return null;
    const [pullRequest] = eligiblePullRequests;
    if (pullRequest === undefined) return null;

    return toTarget(pullRequest);
}

/** Reload mutable PR state before the bot writes an approval or comment. */
export async function refreshTarget(
    params: Omit<DeriveTargetParams, 'trustedHeadSha'> & { target: BotTarget }
): Promise<BotTarget | null> {
    const { data: pullRequest } = await params.octokit.rest.pulls.get({
        owner: params.owner,
        repo: params.repo,
        pull_number: params.target.prNumber
    });
    if (
        pullRequest.state !== 'open' ||
        pullRequest.draft ||
        pullRequest.head.sha !== params.target.headSha ||
        isFork(pullRequest)
    ) {
        return null;
    }
    return toTarget(pullRequest);
}

function toTarget(pullRequest: {
    number: number;
    head: { sha: string };
    base: { ref: string; sha: string };
    labels: Array<{ name?: string }>;
}): BotTarget {
    return {
        prNumber: pullRequest.number,
        headSha: pullRequest.head.sha,
        baseRef: pullRequest.base.ref,
        baseSha: pullRequest.base.sha,
        labels: pullRequest.labels.flatMap((label) =>
            label.name === undefined ? [] : [label.name]
        )
    };
}

function isFork(pullRequest: {
    head: { repo: { fork?: boolean; id?: number } | null };
    base: { repo: { id?: number } };
}): boolean {
    const headRepo = pullRequest.head.repo;
    return (
        headRepo === null ||
        headRepo.fork === true ||
        headRepo.id === undefined ||
        headRepo.id !== pullRequest.base.repo.id
    );
}
