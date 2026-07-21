import { describe, expect, it, vi } from 'vitest';

import type { Octokit } from '../guardrails/context/types';
import { OPT_OUT_LABEL } from '../guardrails/author-opt-out';
import type { Verdict } from '../shared/verdict';
import { runBot } from './run-bot';

const HEAD_SHA = 'abc123';
const BOT_LOGIN = 'fast-track-bot[bot]';

function verdict(overrides: Partial<Verdict> = {}): Verdict {
    return {
        verdict: 'pass',
        guardrails: [{ name: 'dummy', status: 'pass', summary: 'ok' }],
        pr_number: 7,
        head_sha: HEAD_SHA,
        base_ref: 'main',
        base_sha: 'base123',
        ...overrides
    };
}

function pullRequest(overrides: Record<string, unknown> = {}) {
    return {
        number: 7,
        state: 'open',
        draft: false,
        labels: [],
        head: { sha: HEAD_SHA, repo: { id: 1, fork: false } },
        base: { ref: 'main', sha: 'base123', repo: { id: 1 } },
        ...overrides
    };
}

type PullRead = { pr?: unknown; throws?: boolean };

interface FakeOptions {
    existingApproval?: boolean;
    associatedPullRequests?: unknown[];
    // pulls.get gets called twice: once to reload the target before the approval,
    // then once to re-check it afterwards. Configure the return values here.
    reloadBeforeApprove?: PullRead;
    recheckAfterApprove?: PullRead;
}

function fakeOctokit(options: FakeOptions = {}) {
    const listReviews = Symbol('listReviews');
    const listComments = Symbol('listComments');
    const listAssociated = Symbol('listAssociated');
    const reviews = options.existingApproval
        ? [{ id: 1, user: { login: BOT_LOGIN }, state: 'APPROVED', commit_id: HEAD_SHA }]
        : [];
    const associatedPullRequests = options.associatedPullRequests ?? [pullRequest()];
    const pullReads: PullRead[] = [
        options.reloadBeforeApprove ?? { pr: pullRequest() },
        options.recheckAfterApprove ?? { pr: pullRequest() }
    ];
    let getCall = 0;

    const createReview = vi.fn().mockImplementation(async () => {
        reviews.push({
            id: reviews.length + 1,
            user: { login: BOT_LOGIN },
            state: 'APPROVED',
            commit_id: HEAD_SHA
        });
    });
    const dismissReview = vi.fn().mockImplementation(async ({ review_id }) => {
        const review = reviews.find((candidate) => candidate.id === review_id);
        if (review !== undefined) review.state = 'DISMISSED';
    });
    const createComment = vi.fn().mockResolvedValue({});
    const octokit = {
        paginate: vi.fn().mockImplementation(async (route: symbol) => {
            if (route === listReviews)
                return reviews.filter((review) => review.state === 'APPROVED');
            if (route === listComments) return [];
            if (route === listAssociated) return associatedPullRequests;
            return [];
        }),
        rest: {
            repos: {
                listPullRequestsAssociatedWithCommit: listAssociated
            },
            pulls: {
                get: vi.fn().mockImplementation(async () => {
                    const read = pullReads[Math.min(getCall, pullReads.length - 1)] ?? {};
                    getCall += 1;
                    if (read.throws === true) throw new Error('transient GitHub API failure');
                    return { data: read.pr };
                }),
                listReviews,
                createReview,
                dismissReview
            },
            issues: {
                listComments,
                createComment,
                updateComment: vi.fn().mockResolvedValue({})
            }
        }
    } as unknown as Octokit;
    return { octokit, createReview, dismissReview, createComment };
}

function run(value: unknown, options: FakeOptions & { guardrailsSucceeded?: boolean } = {}) {
    const fake = fakeOctokit(options);
    return {
        result: runBot({
            octokit: fake.octokit,
            owner: 'lightly-ai',
            repo: 'lightly-studio',
            trustedHeadSha: HEAD_SHA,
            botLogin: BOT_LOGIN,
            guardrailsSucceeded: options.guardrailsSucceeded ?? true,
            requiredGuardrailNames: ['dummy'],
            verdict: value
        }),
        ...fake
    };
}

describe('runBot', () => {
    it('approves and comments on a current pass', async () => {
        const execution = run(verdict());
        await expect(execution.result).resolves.toEqual({ status: 'approved', prNumber: 7 });
        expect(execution.createReview).toHaveBeenCalledOnce();
        expect(execution.createComment).toHaveBeenCalledOnce();
    });

    it('dismisses an existing approval on a failure verdict', async () => {
        const execution = run(verdict({ verdict: 'fail', reason: 'Human review required.' }), {
            existingApproval: true
        });
        await expect(execution.result).resolves.toEqual({ status: 'dismissed', prNumber: 7 });
        expect(execution.dismissReview).toHaveBeenCalledOnce();
        expect(execution.createComment).toHaveBeenCalledOnce();
    });

    it('uses the current opt-out label instead of a stale pass artifact', async () => {
        const current = pullRequest({ labels: [{ name: OPT_OUT_LABEL }] });
        const execution = run(verdict(), {
            existingApproval: true,
            reloadBeforeApprove: { pr: current }
        });
        await expect(execution.result).resolves.toEqual({ status: 'dismissed', prNumber: 7 });
        expect(execution.createReview).not.toHaveBeenCalled();
        expect(execution.dismissReview).toHaveBeenCalledOnce();
    });

    it('revokes a pass approval if the head changes during the run', async () => {
        const newer = pullRequest({
            head: { sha: 'newer', repo: { id: 1, fork: false } }
        });
        const execution = run(verdict(), { recheckAfterApprove: { pr: newer } });
        await expect(execution.result).resolves.toEqual({ status: 'dismissed', prNumber: 7 });
        expect(execution.createReview).toHaveBeenCalledOnce();
        expect(execution.dismissReview).toHaveBeenCalledOnce();
        expect(execution.createComment).not.toHaveBeenCalled();
    });

    it('dismisses the approval if the post-approval refresh fails', async () => {
        const execution = run(verdict(), { recheckAfterApprove: { throws: true } });
        await expect(execution.result).resolves.toEqual({ status: 'dismissed', prNumber: 7 });
        expect(execution.createReview).toHaveBeenCalledOnce();
        expect(execution.dismissReview).toHaveBeenCalledOnce();
        expect(execution.createComment).not.toHaveBeenCalled();
    });

    it('skips when no eligible PR matches the trusted head', async () => {
        const execution = run(verdict(), { associatedPullRequests: [] });
        await expect(execution.result).resolves.toEqual({
            status: 'skipped',
            reason: 'No eligible PR matched the trusted workflow run.'
        });
        expect(execution.createReview).not.toHaveBeenCalled();
        expect(execution.dismissReview).not.toHaveBeenCalled();
    });
});
