import { writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

import { context, getOctokit } from '@actions/github';

import { ApiGuardrailContext } from './context/api-context';
import { buildVerdict } from './build-verdict';
import { guardrails, selectGuardrails } from './registry';
import { runGuardrails } from './run-guardrails';

// CI entry: runs the guardrails in a PR workflow. Mirrors the local cli.ts but
// swaps git for the read-only GitHub API; it only judges, and writes the verdict
// to a file the bot later consumes (design §2.2). Never holds a write token, never acts.

// cwd-relative, so it lands at fast_track/verdict.json (the workflow's upload path).
const VERDICT_PATH = 'verdict.json';

interface PullRequestEvent {
    number: number;
    head: { sha: string };
    base: { ref: string };
}

function readPullRequest(): PullRequestEvent {
    const pr = context.payload.pull_request;
    if (pr === undefined) {
        throw new Error('No pull_request in the event payload.');
    }
    return pr as PullRequestEvent;
}

async function main(env: NodeJS.ProcessEnv): Promise<void> {
    // Via env, not core.getInput: a `run:` step has no `with:` to feed it.
    const token = env.GITHUB_TOKEN;
    if (token === undefined || token === '') throw new Error('GITHUB_TOKEN is not set.');

    const pr = readPullRequest();
    const octokit = getOctokit(token);

    // Base ref from the event, so stacked / non-main bases diff correctly.
    const guardrailContext = new ApiGuardrailContext({
        octokit,
        owner: context.repo.owner,
        repo: context.repo.repo,
        prNumber: pr.number,
        baseRef: pr.base.ref
    });

    // hasPrContext: true — unlike the local CLI, pr-only guardrails run here.
    const selected = selectGuardrails(guardrails, { hasPrContext: true });
    const run = await runGuardrails(guardrailContext, selected);
    const verdict = buildVerdict(run, { prNumber: pr.number, headSha: pr.head.sha });

    await writeFile(VERDICT_PATH, `${JSON.stringify(verdict, null, 2)}\n`);
    console.log(
        `Verdict: ${verdict.verdict} (${verdict.guardrails.length} guardrail(s)) → ${VERDICT_PATH}`
    );
}

// Only a crash exits non-zero. A `fail` verdict returns cleanly, so it publishes
// as an artifact instead of a broken run masquerading as a passing verdict.
if (process.argv[1] === fileURLToPath(import.meta.url)) {
    main(process.env).catch((error) => {
        console.error(error);
        process.exit(1);
    });
}
