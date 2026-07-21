import type { Octokit } from '../guardrails/context/types';

const DISMISS_MESSAGE = 'Fast Track checks no longer pass; dismissing the bot approval.';
const SUPERSEDED_MESSAGE = 'Superseded by a newer Fast Track approval.';

interface ReviewParams {
    octokit: Octokit;
    owner: string;
    repo: string;
    prNumber: number;
    botLogin: string;
}

interface ApproveParams extends ReviewParams {
    headSha: string;
}

/** Keep exactly one active bot approval, bound to the validated head. */
export async function approve(params: ApproveParams): Promise<'approved' | 'noop'> {
    const reviews = await listBotApprovals(params);
    const current = reviews.find((review) => review.commit_id === params.headSha);

    if (current === undefined) {
        await params.octokit.rest.pulls.createReview({
            owner: params.owner,
            repo: params.repo,
            pull_number: params.prNumber,
            commit_id: params.headSha,
            event: 'APPROVE'
        });
    }

    await dismissReviews(
        params,
        reviews.filter((review) => review !== current),
        SUPERSEDED_MESSAGE
    );
    return current === undefined ? 'approved' : 'noop';
}

/** Dismiss only the App's active approvals, never a human review. */
export async function dismissApproval(params: ReviewParams): Promise<number> {
    const reviews = await listBotApprovals(params);
    await dismissReviews(params, reviews, DISMISS_MESSAGE);
    return reviews.length;
}

async function listBotApprovals(params: ReviewParams) {
    const reviews = await params.octokit.paginate(params.octokit.rest.pulls.listReviews, {
        owner: params.owner,
        repo: params.repo,
        pull_number: params.prNumber
    });
    return reviews.filter(
        (review) => review.user?.login === params.botLogin && review.state === 'APPROVED'
    );
}

async function dismissReviews(
    params: ReviewParams,
    reviews: Awaited<ReturnType<typeof listBotApprovals>>,
    message: string
): Promise<void> {
    for (const review of reviews) {
        await params.octokit.rest.pulls.dismissReview({
            owner: params.owner,
            repo: params.repo,
            pull_number: params.prNumber,
            review_id: review.id,
            message
        });
    }
}
