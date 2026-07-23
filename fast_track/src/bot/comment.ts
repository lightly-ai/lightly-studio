import type { Octokit } from '../shared/octokit';
import type { Verdict } from '../shared/verdict';

const COMMENT_MARKER = '<!-- fast-track-bot -->';
const HEADLINES: Record<Verdict['verdict'], string> = {
    pass: '✅&nbsp; Fast Track: all required checks passed — auto-approved.',
    fail: '❌&nbsp; Fast Track: checks did not pass',
    opt_out: '⏭️&nbsp; Fast Track skipped — deferring to human review'
};

interface UpsertCommentParams {
    octokit: Octokit;
    owner: string;
    repo: string;
    prNumber: number;
    botLogin: string;
    body: string;
}

interface RenderCommentParams {
    verdict: Verdict;
    headSha: string;
    /** Link to the guardrail run; omitted when it is unknown. */
    runUrl?: string;
}

/** Render the human-visible part of the bot's single status comment. */
export function renderComment(params: RenderCommentParams): string {
    const { verdict, headSha, runUrl } = params;
    const lines = [`### ${HEADLINES[verdict.verdict]}`];
    // Without guardrail rows (an opt-out or a synthesized failure) the reason is
    // the only diagnosis, so surface it; otherwise the table already carries it.
    if (
        verdict.verdict !== 'pass' &&
        verdict.reason !== undefined &&
        verdict.guardrails.length === 0
    ) {
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

    if (runUrl !== undefined) {
        lines.push('', `[View the guardrail run](${runUrl})`);
    }

    lines.push(
        '',
        'To run the guardrails locally, from `fast_track/` run `make install` once, then ' +
            '`make run-guardrails` (or `GUARDRAILS=<name1>,<name2> make run-guardrails` for some guardrails).'
    );

    lines.push('', `<sub>Reflects \`${headSha.slice(0, 7)}\`.</sub>`);
    return lines.join('\n');
}

/** Find the App's existing marked comment, or `undefined` if it has none yet. */
async function findBotComment(
    params: Pick<UpsertCommentParams, 'octokit' | 'owner' | 'repo' | 'prNumber' | 'botLogin'>
): Promise<{ id: number; body: string } | undefined> {
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
    return existing === undefined ? undefined : { id: existing.id, body: existing.body ?? '' };
}

/** Create or edit the App's marked comment, leaving all other comments alone. */
export async function upsertComment(
    params: UpsertCommentParams
): Promise<'created' | 'updated' | 'noop'> {
    const fullBody = `${COMMENT_MARKER}\n${params.body}`;
    const existing = await findBotComment(params);

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
