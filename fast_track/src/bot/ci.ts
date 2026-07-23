import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

import { context, getOctokit } from '@actions/github';

import { guardrails } from '../guardrails/registry';
import { runBot } from './run-bot';

// The verdict comes from code in the pull request, so it can be faked. That is
// fine: a faked pass only earns the bot's approval, which still cannot merge the
// pull request on its own. Safety rests on this, not on trusting the verdict.
const VERDICT_PATH = 'verdict/verdict.json';

async function main(env: NodeJS.ProcessEnv): Promise<void> {
    const token = requiredEnv(env, 'GITHUB_TOKEN');
    const trustedHeadSha = requiredEnv(env, 'HEAD_SHA');
    const headBranch = requiredEnv(env, 'HEAD_BRANCH');
    const appSlug = requiredEnv(env, 'APP_SLUG');
    const guardrailConclusion = requiredEnv(env, 'GUARDRAIL_CONCLUSION');
    const guardrailWorkflowId = requiredIntEnv(env, 'GUARDRAIL_WORKFLOW_ID');
    const guardrailRunNumber = requiredIntEnv(env, 'GUARDRAIL_RUN_NUMBER');
    const guardrailRunAttempt = requiredIntEnv(env, 'GUARDRAIL_RUN_ATTEMPT');
    const verdict = await readVerdict();

    const result = await runBot({
        octokit: getOctokit(token),
        owner: context.repo.owner,
        repo: context.repo.repo,
        trustedHeadSha,
        headBranch,
        botLogin: `${appSlug}[bot]`,
        guardrailsSucceeded: guardrailConclusion === 'success',
        requiredGuardrailNames: guardrails
            .filter((guardrail) => guardrail.required)
            .map((guardrail) => guardrail.name),
        guardrailWorkflowId,
        guardrailRunNumber,
        guardrailRunAttempt,
        verdict
    });
    console.log(JSON.stringify(result));
}

async function readVerdict(): Promise<unknown> {
    try {
        return JSON.parse(await readFile(VERDICT_PATH, 'utf8')) as unknown;
    } catch (error) {
        console.warn(`Could not read a valid verdict from ${VERDICT_PATH}.`, error);
        return undefined;
    }
}

function requiredEnv(env: NodeJS.ProcessEnv, name: string): string {
    const value = env[name];
    if (value === undefined || value === '') throw new Error(`${name} is not set.`);
    return value;
}

function requiredIntEnv(env: NodeJS.ProcessEnv, name: string): number {
    const value = requiredEnv(env, name);
    const parsed = Number(value);
    if (!Number.isInteger(parsed)) throw new Error(`${name} is not an integer: ${value}`);
    return parsed;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
    main(process.env).catch((error) => {
        console.error(error);
        process.exit(1);
    });
}
