import type { Octokit } from '../shared/octokit';

const DISMISS_MESSAGE = 'Fast Track checks no longer pass; dismissing the bot approval.';

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

/**
 * Approve only when no bot approval exists yet.
 */
export async function approve(params: ApproveParams): Promise<'approved' | 'noop'> {
    const reviews = await listBotApprovals(params);
    if (reviews.length > 0) return 'noop';

    await params.octokit.rest.pulls.createReview({
        owner: params.owner,
        repo: params.repo,
        pull_number: params.prNumber,
        commit_id: params.headSha,
        event: 'APPROVE'
    });
    return 'approved';
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
