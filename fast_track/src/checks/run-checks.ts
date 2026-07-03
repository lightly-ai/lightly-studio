import { writeFileSync } from 'node:fs';

import * as core from '@actions/core';
import * as github from '@actions/github';

import { ApiGuardrailContext } from '../guardrails/context/api-context';
import { guardrails, selectGuardrails } from '../guardrails/registry';
import { runGuardrails } from '../guardrails/run-guardrails';
import { buildVerdict } from './verdict';

/** Where the verdict is serialized; the workflow uploads this as an artifact. */
const VERDICT_PATH = 'verdict.json';

/** The `pull_request` fields Checks needs from the event payload. */
interface PullRequestEvent {
    number: number;
    head: { sha: string };
    base: { ref: string };
    draft?: boolean;
}

/**
 * Fast Track Checks entry point (CI only). Runs in PR context with a read-only
 * token, judges the PR against the guardrails, and writes the verdict to disk.
 * The job succeeds whatever the verdict is — a `fail` is a normal, published
 * outcome, not a job failure. `setFailed` is reserved for genuine errors (a
 * missing token or a crash), which leave no verdict for the Bot to act on.
 */
async function main(): Promise<void> {
    const token = process.env.GITHUB_TOKEN;
    if (!token) {
        core.setFailed('GITHUB_TOKEN is not set.');
        return;
    }

    const pr = github.context.payload.pull_request as PullRequestEvent | undefined;
    if (pr === undefined) {
        core.info('No pull_request in the event payload; nothing to judge.');
        return;
    }

    const { owner, repo } = github.context.repo;
    const octokit = github.getOctokit(token);
    // Base ref from the event, so a stacked PR (non-main base) diffs correctly.
    const context = new ApiGuardrailContext(
        octokit,
        { owner, repo, pull_number: pr.number },
        pr.base.ref
    );

    // CI has PR context, so pr-only guardrails run here (unlike the local CLI).
    const selected = selectGuardrails(guardrails, { hasPrContext: true });
    const run = await runGuardrails(context, selected);
    const verdict = buildVerdict(run, { pr_number: pr.number, head_sha: pr.head.sha });

    writeFileSync(VERDICT_PATH, `${JSON.stringify(verdict, null, 2)}\n`);
    core.info(`Verdict: ${verdict.verdict} (${verdict.guardrails.length} guardrail(s)).`);
    core.setOutput('verdict', verdict.verdict);
}

main().catch((error: unknown) => {
    core.setFailed(error instanceof Error ? error.message : String(error));
});
