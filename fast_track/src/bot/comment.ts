import type { Octokit } from '../guardrails/context/types';
import type { Verdict } from '../shared/verdict';

const COMMENT_MARKER = '<!-- fast-track-bot -->';
const HEADLINES: Record<Verdict['verdict'], string> = {
    pass: '✅ Fast Track: all required checks passed — auto-approved.',
    fail: '❌ Fast Track: checks did not pass',
    opt_out: '⏭️ Fast Track skipped — deferring to human review'
};

interface UpsertCommentParams {
    octokit: Octokit;
    owner: string;
    repo: string;
    prNumber: number;
    botLogin: string;
    body: string;
}

/** Render the human-visible part of the bot's single status comment. */
export function renderComment(verdict: Verdict, headSha: string): string {
    const lines = [`### ${HEADLINES[verdict.verdict]}`];
    if (verdict.verdict !== 'pass' && verdict.reason !== undefined) {
        lines.push('', verdict.reason);
    }

    if (verdict.guardrails.length === 0) {
        lines.push('', '_No guardrails were run._');
    } else {
        lines.push('', '| Guardrail | Result | Message |', '|---|---|---|');
        for (const guardrail of verdict.guardrails) {
            const icon = guardrail.status === 'pass' ? '✅' : '❌';
            lines.push(
                `| ${escapeCell(guardrail.name)} | ${icon} | ${escapeCell(guardrail.summary)} |`
            );
        }
    }

    lines.push('', `<sub>Reflects \`${headSha.slice(0, 7)}\`.</sub>`);
    return lines.join('\n');
}

/** Create or edit the App's marked comment, leaving all other comments alone. */
export async function upsertComment(
    params: UpsertCommentParams
): Promise<'created' | 'updated' | 'noop'> {
    const fullBody = `${COMMENT_MARKER}\n${params.body}`;
    const comments = await params.octokit.paginate(params.octokit.rest.issues.listComments, {
        owner: params.owner,
        repo: params.repo,
        issue_number: params.prNumber
    });
    const existing = comments.find(
        (comment) =>
            comment.user?.login === params.botLogin &&
            (comment.body ?? '').startsWith(COMMENT_MARKER)
    );

    if (existing === undefined) {
        await params.octokit.rest.issues.createComment({
            owner: params.owner,
            repo: params.repo,
            issue_number: params.prNumber,
            body: fullBody
        });
        return 'created';
    }
    if (existing.body === fullBody) return 'noop';

    await params.octokit.rest.issues.updateComment({
        owner: params.owner,
        repo: params.repo,
        comment_id: existing.id,
        body: fullBody
    });
    return 'updated';
}

function escapeCell(value: string): string {
    return value.replace(/\r?\n/g, ' ').replace(/\|/g, '\\|');
}
