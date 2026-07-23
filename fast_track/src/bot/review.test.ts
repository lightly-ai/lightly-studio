import { describe, expect, it, vi } from 'vitest';

import type { Octokit } from '../shared/octokit';
import { approve, dismissApproval } from './review';

const BOT_LOGIN = 'fast-track-bot[bot]';
const HEAD_SHA = 'abc123';

interface FakeReview {
    id: number;
    login: string;
    state: string;
    commitId: string;
}

function fakeOctokit(reviews: FakeReview[]) {
    const listReviews = Symbol('listReviews');
    const createReview = vi.fn().mockResolvedValue({});
    const dismissReview = vi.fn().mockResolvedValue({});
    const octokit = {
        paginate: vi.fn().mockResolvedValue(
            reviews.map((review) => ({
                id: review.id,
                user: { login: review.login },
                state: review.state,
                commit_id: review.commitId
            }))
        ),
        rest: { pulls: { listReviews, createReview, dismissReview } }
    } as unknown as Octokit;
    return { octokit, createReview, dismissReview };
}

function buildReviewParams(octokit: Octokit) {
    return {
        octokit,
        owner: 'lightly-ai',
        repo: 'lightly-studio',
        prNumber: 7,
        headSha: HEAD_SHA,
        botLogin: BOT_LOGIN
    };
}

describe('approve', () => {
    it('creates the first approval', async () => {
        const fake = fakeOctokit([]);
        await expect(approve(buildReviewParams(fake.octokit))).resolves.toBe('approved');
        expect(fake.createReview).toHaveBeenCalledWith(
            expect.objectContaining({ commit_id: HEAD_SHA, event: 'APPROVE' })
        );
    });

    it('does nothing when the bot already approved the validated head', async () => {
        const fake = fakeOctokit([
            { id: 1, login: BOT_LOGIN, state: 'APPROVED', commitId: HEAD_SHA }
        ]);
        await expect(approve(buildReviewParams(fake.octokit))).resolves.toBe('noop');
        expect(fake.createReview).not.toHaveBeenCalled();
        expect(fake.dismissReview).not.toHaveBeenCalled();
    });

    it('refreshes an approval and dismisses the superseded one', async () => {
        const fake = fakeOctokit([{ id: 1, login: BOT_LOGIN, state: 'APPROVED', commitId: 'old' }]);
        await expect(approve(buildReviewParams(fake.octokit))).resolves.toBe('approved');
        expect(fake.createReview).toHaveBeenCalledOnce();
        expect(fake.dismissReview).toHaveBeenCalledWith(expect.objectContaining({ review_id: 1 }));
    });

    it('keeps only one approval when duplicate approvals exist for the current head', async () => {
        const fake = fakeOctokit([
            { id: 1, login: BOT_LOGIN, state: 'APPROVED', commitId: HEAD_SHA },
            { id: 2, login: BOT_LOGIN, state: 'APPROVED', commitId: HEAD_SHA }
        ]);
        await expect(approve(buildReviewParams(fake.octokit))).resolves.toBe('noop');
        expect(fake.createReview).not.toHaveBeenCalled();
        expect(fake.dismissReview).toHaveBeenCalledOnce();
    });
});

describe('dismissApproval', () => {
    it('dismisses only the bot approval', async () => {
        const fake = fakeOctokit([
            { id: 1, login: BOT_LOGIN, state: 'APPROVED', commitId: HEAD_SHA },
            { id: 2, login: 'human', state: 'APPROVED', commitId: HEAD_SHA },
            { id: 3, login: BOT_LOGIN, state: 'COMMENTED', commitId: HEAD_SHA }
        ]);
        await expect(dismissApproval(buildReviewParams(fake.octokit))).resolves.toBe(1);
        expect(fake.dismissReview).toHaveBeenCalledOnce();
        expect(fake.dismissReview).toHaveBeenCalledWith(expect.objectContaining({ review_id: 1 }));
    });
});
