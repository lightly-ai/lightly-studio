import type { Octokit } from '../shared/octokit';

/** `listWorkflowRuns` caps per_page at 100. */
const PER_PAGE = 100;

export interface SupersededRunParams {
    octokit: Octokit;
    owner: string;
    repo: string;
    /** The head SHA the triggering guardrail run judged. */
    headSha: string;
    /** The head branch the triggering run ran on. Two branches can share a head
     *  SHA, so the comparison is scoped to this branch to ignore unrelated runs. */
    headBranch: string;
    /**
     * The guardrail workflow whose runs are compared. `run_number` only
     * increases within one workflow, so the comparison is scoped to it.
     */
    workflowId: number;
    /** `run_number` of the guardrail run that triggered this bot execution. */
    runNumber: number;
    /** `run_attempt` of the triggering run. A re-run keeps `run_number` and
     *  bumps this, so recency compares the (run_number, run_attempt) pair. */
    runAttempt: number;
}

/**
 * Whether a newer guardrail run for the same head has already reached a real
 * conclusion, which makes the triggering run stale.
 *
 * `workflow_run` events can arrive out of order, so a late event from a
 * cancelled early run can reach the bot after a newer run has already approved.
 * The two runs share a head, so only run recency can tell them apart; a stale
 * run must skip rather than dismiss the newer run's fresh approval.
 *
 * Only a `completed`, non-`skipped` run supersedes: a `skipped` run (from a
 * title/body edit) carries no judgment, so treating it as superseding would
 * leave a passing PR unapproved. A read error returns `false` so the bot still
 * runs, since skipping would drop a genuine dismissal.
 */
export async function isSupersededRun(params: SupersededRunParams): Promise<boolean> {
    const { octokit, owner, repo, headSha, headBranch, workflowId, runNumber, runAttempt } = params;
    try {
        // Walk every page: a superseding run could sit on any of them.
        const runs = await octokit.paginate(octokit.rest.actions.listWorkflowRuns, {
            owner,
            repo,
            workflow_id: workflowId,
            head_sha: headSha,
            branch: headBranch,
            per_page: PER_PAGE
        });
        return runs.some(
            (run) =>
                isNewerRun(run, runNumber, runAttempt) &&
                run.status === 'completed' &&
                run.conclusion !== 'skipped'
        );
    } catch (error) {
        console.warn('Fast Track: could not check for superseding runs; proceeding.', error);
        return false;
    }
}

/** Recency order on the (run_number, run_attempt) pair. The run listing reports
 *  each run at its latest attempt, so a re-run supersedes its earlier attempts. */
function isNewerRun(
    run: { run_number: number; run_attempt?: number },
    runNumber: number,
    runAttempt: number
): boolean {
    if (run.run_number !== runNumber) return run.run_number > runNumber;
    return (run.run_attempt ?? 1) > runAttempt;
}
