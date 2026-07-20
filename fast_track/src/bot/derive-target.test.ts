import { describe, expect, it, vi } from 'vitest';

import type { Octokit } from '../guardrails/context/types';
import { deriveTarget, refreshTarget, type BotTarget } from './derive-target';

const HEAD_SHA = 'abc123';

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

/**
 * A fake Octokit whose `paginate` returns `pullRequests` (as the real one does
 * after walking every page). `listPullRequestsAssociatedWithCommit` is a
 * sentinel so a test can assert we hand *that* endpoint to `paginate`.
 */
function fakeOctokit(pullRequests: unknown[], current = pullRequest()): Octokit {
    return {
        paginate: vi.fn().mockResolvedValue(pullRequests),
        rest: {
            repos: { listPullRequestsAssociatedWithCommit: 'assoc-endpoint' },
            pulls: { get: vi.fn().mockResolvedValue({ data: current }) }
        }
    } as unknown as Octokit;
}

function derive(pullRequests: unknown[]) {
    return deriveTarget({
        octokit: fakeOctokit(pullRequests),
        owner: 'lightly-ai',
        repo: 'lightly-studio',
        trustedHeadSha: HEAD_SHA
    });
}

describe('deriveTarget', () => {
    it('returns the internal open PR bound to the trusted head', async () => {
        await expect(derive([pullRequest()])).resolves.toEqual({
            prNumber: 7,
            headSha: HEAD_SHA,
            baseRef: 'main',
            baseSha: 'base123',
            labels: []
        });
    });

    it('refuses to guess when multiple internal PRs share the trusted head', async () => {
        await expect(derive([pullRequest(), pullRequest({ number: 8 })])).resolves.toBeNull();
    });

    it('walks every page so a second candidate cannot hide behind pagination', async () => {
        const octokit = fakeOctokit([pullRequest(), pullRequest({ number: 8 })]);
        await expect(
            deriveTarget({
                octokit,
                owner: 'lightly-ai',
                repo: 'lightly-studio',
                trustedHeadSha: HEAD_SHA
            })
        ).resolves.toBeNull();
        expect(octokit.paginate).toHaveBeenCalledWith('assoc-endpoint', {
            owner: 'lightly-ai',
            repo: 'lightly-studio',
            commit_sha: HEAD_SHA,
            per_page: 100
        });
    });

    it('ignores superseded, closed, and draft PRs', async () => {
        await expect(
            derive([pullRequest({ head: { sha: 'newer', repo: { id: 1, fork: false } } })])
        ).resolves.toBeNull();
        await expect(derive([pullRequest({ state: 'closed' })])).resolves.toBeNull();
        await expect(derive([pullRequest({ draft: true })])).resolves.toBeNull();
    });

    it('refuses cross-repository, explicit, and deleted forks', async () => {
        const crossRepo = pullRequest({ head: { sha: HEAD_SHA, repo: { id: 2, fork: false } } });
        const explicitFork = pullRequest({
            head: { sha: HEAD_SHA, repo: { id: 1, fork: true } }
        });
        const deletedFork = pullRequest({ head: { sha: HEAD_SHA, repo: null } });

        await expect(derive([crossRepo])).resolves.toBeNull();
        await expect(derive([explicitFork])).resolves.toBeNull();
        await expect(derive([deletedFork])).resolves.toBeNull();
    });
});

describe('refreshTarget', () => {
    const target: BotTarget = {
        prNumber: 7,
        headSha: HEAD_SHA,
        baseRef: 'main',
        baseSha: 'base123',
        labels: []
    };

    it('reloads the current base and labels', async () => {
        const octokit = fakeOctokit([], pullRequest({ labels: [{ name: 'bug' }] }));
        await expect(
            refreshTarget({ octokit, owner: 'lightly-ai', repo: 'lightly-studio', target })
        ).resolves.toEqual({ ...target, labels: ['bug'] });
    });

    it('rejects a target whose head changed before mutation', async () => {
        const current = pullRequest({ head: { sha: 'newer', repo: { id: 1, fork: false } } });
        const octokit = fakeOctokit([], current);
        await expect(
            refreshTarget({ octokit, owner: 'lightly-ai', repo: 'lightly-studio', target })
        ).resolves.toBeNull();
    });
});
