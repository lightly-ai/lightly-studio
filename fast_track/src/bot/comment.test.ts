import { describe, expect, it, vi } from 'vitest';

import type { Octokit } from '../shared/octokit';
import type { Verdict } from '../shared/verdict';
import { renderComment, upsertComment } from './comment';

const BOT_LOGIN = 'fast-track-bot[bot]';
const HEAD_SHA = 'abc1234def';
const MARKER = '<!-- fast-track-bot -->';

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

describe('renderComment', () => {
    it('renders pass, fail, and opt-out states', () => {
        expect(renderComment({ verdict: verdict(), headSha: HEAD_SHA })).toContain(
            '✅&nbsp; Fast Track'
        );
        expect(
            renderComment({
                verdict: verdict({ verdict: 'fail', reason: 'failed' }),
                headSha: HEAD_SHA
            })
        ).toContain('❌&nbsp; Fast Track: checks did not pass');
        expect(
            renderComment({
                verdict: verdict({
                    verdict: 'opt_out',
                    reason: 'Author opted out.',
                    guardrails: []
                }),
                headSha: HEAD_SHA
            })
        ).toContain('⏭️&nbsp; Fast Track skipped');
    });

    it('surfaces the reason only when no guardrail rows carry it', () => {
        // A guardrail-level fail lists its rows, so the reason would be redundant.
        expect(
            renderComment({
                verdict: verdict({ verdict: 'fail', reason: 'lint failed' }),
                headSha: HEAD_SHA
            })
        ).not.toContain('lint failed');
        // A synthesized fail and an opt-out have no rows, so the reason is the diagnosis.
        expect(
            renderComment({
                verdict: verdict({
                    verdict: 'fail',
                    reason: 'Workflow did not complete.',
                    guardrails: []
                }),
                headSha: HEAD_SHA
            })
        ).toContain('Workflow did not complete.');
        expect(
            renderComment({
                verdict: verdict({
                    verdict: 'opt_out',
                    reason: 'Author opted out.',
                    guardrails: []
                }),
                headSha: HEAD_SHA
            })
        ).toContain('Author opted out.');
    });

    it('links the guardrail run when a URL is given', () => {
        const url = 'https://github.com/lightly-ai/lightly-studio/actions/runs/123';
        expect(renderComment({ verdict: verdict(), headSha: HEAD_SHA, runUrl: url })).toContain(
            `(${url})`
        );
        expect(renderComment({ verdict: verdict(), headSha: HEAD_SHA })).not.toContain(
            'View the guardrail run'
        );
    });

    it('always includes the local-repro hint', () => {
        expect(renderComment({ verdict: verdict(), headSha: HEAD_SHA })).toContain(
            'make run-guardrails'
        );
        expect(
            renderComment({ verdict: verdict({ verdict: 'fail', reason: 'x' }), headSha: HEAD_SHA })
        ).toContain('make run-guardrails');
    });

    it('renders guardrails safely in a Markdown table', () => {
        const body = renderComment({
            verdict: verdict({
                guardrails: [{ name: 'lint|check', status: 'fail', summary: 'one\ntwo|three' }]
            }),
            headSha: HEAD_SHA
        });
        expect(body).toContain('| lint\\|check | ❌ | one two\\|three |');
        expect(body).toContain('<sub>Reflects `abc1234`.</sub>');
    });
});

function fakeOctokit(comments: Array<{ id: number; login: string; body: string }>) {
    const listComments = Symbol('listComments');
    const createComment = vi.fn().mockResolvedValue({});
    const updateComment = vi.fn().mockResolvedValue({});
    const octokit = {
        paginate: vi.fn().mockResolvedValue(
            comments.map((comment) => ({
                id: comment.id,
                user: { login: comment.login },
                body: comment.body
            }))
        ),
        rest: { issues: { listComments, createComment, updateComment } }
    } as unknown as Octokit;
    return { octokit, createComment, updateComment };
}

function upsert(octokit: Octokit) {
    return upsertComment({
        octokit,
        owner: 'lightly-ai',
        repo: 'lightly-studio',
        prNumber: 7,
        botLogin: BOT_LOGIN,
        body: 'new status'
    });
}

describe('upsertComment', () => {
    it('creates the first marked comment', async () => {
        const fake = fakeOctokit([]);
        await expect(upsert(fake.octokit)).resolves.toBe('created');
        expect(fake.createComment).toHaveBeenCalledWith(
            expect.objectContaining({ body: `${MARKER}\nnew status` })
        );
    });

    it('updates the existing marked bot comment', async () => {
        const fake = fakeOctokit([{ id: 3, login: BOT_LOGIN, body: `${MARKER}\nold status` }]);
        await expect(upsert(fake.octokit)).resolves.toBe('updated');
        expect(fake.updateComment).toHaveBeenCalledWith(
            expect.objectContaining({ comment_id: 3, body: `${MARKER}\nnew status` })
        );
    });

    it('does not edit an identical comment', async () => {
        const fake = fakeOctokit([{ id: 3, login: BOT_LOGIN, body: `${MARKER}\nnew status` }]);
        await expect(upsert(fake.octokit)).resolves.toBe('noop');
        expect(fake.updateComment).not.toHaveBeenCalled();
    });

    it('ignores comments from other authors and unmarked bot comments', async () => {
        const fake = fakeOctokit([
            { id: 1, login: 'a-human', body: `${MARKER}\nlooks like ours but is not` },
            { id: 2, login: BOT_LOGIN, body: 'an unmarked bot comment' }
        ]);
        await expect(upsert(fake.octokit)).resolves.toBe('created');
        expect(fake.createComment).toHaveBeenCalled();
        expect(fake.updateComment).not.toHaveBeenCalled();
    });
});
